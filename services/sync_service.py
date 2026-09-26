"""Synchronisation descendante : serveur -> base locale de chaque poste.

Les ecritures locales sont deja poussees vers le serveur
(repositories.base._route_write + file_attente_synchro). Ce module fait
le chemin inverse : recuperer du serveur la structure de l'ecole (cycles,
classes, matieres, annees scolaires, tarifs) et l'appliquer a la base
locale. Ainsi, toute modification faite sur le compte directeur est
repercutee sur les autres postes/utilisateurs des qu'ils sont connectes.

Correspondance par cles naturelles stables (noms, libelles) : les id
auto-increments peuvent differer entre le serveur et chaque machine.
Chaque section est indépendante : un echec n'annule pas les autres.
"""

import uuid

from database import db


def _champ(row, *aliases, default=None):
    for cle in aliases:
        if cle in row and row[cle] is not None:
            return row[cle]
    return default


def _bool_int(valeur):
    """Convertit une valeur SQL/JSON ('1', 1, 'oui', 'vrai', True...) en 0/1."""
    if valeur is None:
        return 0
    if isinstance(valeur, bool):
        return 1 if valeur else 0
    if isinstance(valeur, (int, float)):
        return 1 if valeur else 0
    return 1 if str(valeur).strip().lower() in ("1", "vrai", "oui", "actif",
                                                "true", "yes") else 0


# Le serveur stocke le statut d'un eleve dans son propre vocabulaire
# (actif / inactif / exclu) ; l'interface filtre et compte sur
# « Inscrit / Pre-inscrit / Inactif ». Sans traduction, un eleve rapatrie
# etait invisible sous TOUS les filtres de statut et ses KPI etaient faux.
_STATUTS_LOCAL_ELEVE = ("Inscrit", "Pre-inscrit", "Inactif")


def _statut_eleve_local(valeur, default="Inscrit"):
    s = str(valeur if valeur is not None else "").strip()
    if s in _STATUTS_LOCAL_ELEVE:
        return s
    s = s.lower()
    correspondance = {
        "actif": "Inscrit", "inscrit": "Inscrit", "en règle": "Inscrit",
        "en regle": "Inscrit",
        "pre-inscrit": "Pre-inscrit", "preinscrit": "Pre-inscrit",
        "pré-inscrit": "Pre-inscrit", "pre": "Pre-inscrit",
        "inactif": "Inactif", "suspendu": "Inactif", "abandon": "Inactif",
        "exclu": "Inactif", "exclus": "Inactif", "radié": "Inactif",
        "radie": "Inactif",
    }
    return correspondance.get(s, default)


def _coef_float(valeur):
    """Convertit une valeur numerique (eventuellement '1,5' francais) en float."""
    if valeur is None:
        return 0.0
    if isinstance(valeur, (int, float)):
        return float(valeur)
    texte = str(valeur).strip().replace(",", ".")
    try:
        return float(texte)
    except ValueError:
        return 0.0


def _upsert(table, cle_where, params_where, colonnes, valeurs):
    """INSERT ou UPDATE par cle naturelle ; renvoie l'id local."""
    existant = db.query_one(f"SELECT id FROM {table} WHERE {cle_where}", params_where)
    if existant:
        assignments = ", ".join(f"{c} = ?" for c in colonnes)
        db.execute(
            f"UPDATE {table} SET {assignments} WHERE id = ?",
            (*valeurs, existant["id"]))
        return existant["id"]
    cols = ", ".join(colonnes)
    marks = ", ".join("?" for _ in colonnes)
    return db.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({marks})", valeurs)


def _noms_creations_pending():
    """Noms des cycles/matieres/classes crees hors-ligne (POST en file
    PENDING, encore non pousses). Le mirroir du pull ne doit pas les
    supprimer : le drain les poussera ensuite au serveur."""
    noms = {"cycles": set(), "matieres": set(), "classes": set()}
    try:
        for r in db.query(
                "SELECT endpoint, payload FROM file_attente_synchro"
                " WHERE status = 'PENDING'"):
            import json as _json
            try:
                p = _json.loads(r["payload"])
            except (ValueError, TypeError):
                continue
            if not isinstance(p, dict):
                continue
            ep = (r["endpoint"] or "")
            nom = _champ(p, "nom", "name", "classe", "cycle") or ""
            if not nom:
                continue
            if ep == "/cycle":
                noms["cycles"].add(nom)
            elif ep == "/matiere":
                noms["matieres"].add(nom)
            elif ep == "/classe":
                noms["classes"].add(nom)
    except Exception:
        pass
    return noms


def _supprimer_absents(table, noms_srv, resultat, pends=None):
    """Propage les suppressions faites sur le serveur, SANS risque :
    une ligne locale absente du serveur n'est supprimee que si aucune
    donnee locale ne en depend (sinon elle est conservee et signalee).
    Les creations hors-ligne (POST PENDING) sont aussi protegees : le
    drain les enverra, le mirroir ne doit pas les annuler."""
    gardes = []
    pends = pends or {}
    pend_table = pends.get(table, set())
    if table == "cycles":
        locaux = db.query("SELECT id, nom FROM cycles")
        for r in locaux:
            if r["nom"] in noms_srv or r["nom"] in pend_table:
                continue
            if db.query_one(
                    "SELECT id FROM classes WHERE cycle_id = ? LIMIT 1",
                    (r["id"],)):
                gardes.append(r["nom"])
                continue
            # Protection : cycle qui a des eleves via ses classes
            if db.query_one(
                    """SELECT 1 FROM eleves e
                       JOIN classes c ON c.id = e.classe_id
                       WHERE c.cycle_id = ? LIMIT 1""", (r["id"],)):
                gardes.append(r["nom"])
                continue
            db.execute("DELETE FROM cycles WHERE id = ?", (r["id"],))
            resultat["suppressions"] += 1
    elif table == "matieres":
        locaux = db.query("SELECT id, nom FROM matieres")
        for r in locaux:
            if r["nom"] in noms_srv or r["nom"] in pend_table:
                continue
            if db.query_one(
                    "SELECT id FROM programmes WHERE matiere_id = ? LIMIT 1",
                    (r["id"],)):
                gardes.append(r["nom"])
                continue
            # Protection : matiere qui a des notes locales
            if db.query_one(
                    "SELECT id FROM notes WHERE matiere_id = ? LIMIT 1", (r["id"],)):
                gardes.append(r["nom"])
                continue
            db.execute("DELETE FROM matieres WHERE id = ?", (r["id"],))
            resultat["suppressions"] += 1
    elif table == "classes":
        locaux = db.query("SELECT id, nom FROM classes")
        for r in locaux:
            if r["nom"] in noms_srv or r["nom"] in pend_table:
                continue
            depend = db.query_one(
                """SELECT e.id FROM eleves e WHERE e.classe_id = ?
                   UNION ALL SELECT t.id FROM tarifs t WHERE t.classe_id = ?
                   UNION ALL SELECT p.id FROM planning p WHERE p.classe_id = ?
                   UNION ALL SELECT pr.id FROM programmes pr WHERE pr.classe_id = ?
                   UNION ALL SELECT n.id FROM notes n
                     JOIN eleves e ON e.id = n.eleve_id WHERE e.classe_id = ?
                   UNION ALL SELECT p.id FROM presences p
                     JOIN eleves e ON e.id = p.eleve_id WHERE e.classe_id = ?
                   UNION ALL SELECT pa.id FROM paiements pa
                     JOIN eleves e ON e.id = pa.eleve_id WHERE e.classe_id = ?
                   LIMIT 1""",
                (r["id"], r["id"], r["id"], r["id"], r["id"], r["id"], r["id"]))
            if depend:
                gardes.append(r["nom"])
                continue
            db.execute("DELETE FROM classes WHERE id = ?", (r["id"],))
            resultat["suppressions"] += 1
    if gardes:
        # Information (pas une erreur) : le poste garde ces lignes car
        # des donnees locales y sont encore rattachees.
        resultat.setdefault("conserves", []).extend(
            f"{table}:{nom}" for nom in sorted(gardes))


def pull_structure():
    """Recupere la structure de l'ecole depuis le serveur.

    Renvoie un dict {section: nb_lignes_appliquees, "suppressions": n,
    "conserves": [...], "erreurs": [...]}. Une ligne locale absente du
    serveur n'est supprimee que si aucune donnee n'en depend.
    """
    from api import client

    resultat = {"cycles": 0, "classes": 0, "matieres": 0, "annees": 0,
                "tarifs": 0, "suppressions": 0, "conserves": [],
                "erreurs": []}
    pends = _noms_creations_pending()

    # ---------- Cycles ----------
    cycles_srv = []
    noms_cycles_srv = set()
    try:
        data, err = client.cycles()
        if err:
            raise RuntimeError(err)
        cycles_srv = data or []
        cycle_ids_srv = {}
        for c in cycles_srv:
            nom = _champ(c, "nom", "name", "cycle")
            if not nom:
                continue
            noms_cycles_srv.add(nom)
            local_id = _upsert(
                "cycles", "nom = ?", (nom,),
                ["description"], [_champ(c, "description", "libelle") or ""])
            cycle_ids_srv[c.get("id")] = (nom, local_id)
            resultat["cycles"] += 1
        if noms_cycles_srv:
            # Suppressions propagees : uniquement les lignes vides locales.
            _supprimer_absents("cycles", noms_cycles_srv, resultat, pends)
    except Exception as exc:
        resultat["erreurs"].append(f"cycles: {exc}")

    # ---------- Matieres ----------
    try:
        data, err = client.matieres()
        if err:
            raise RuntimeError(err)
        noms_srv = {_champ(m, "nom", "name", "matiere")
                    for m in data or [] if _champ(m, "nom", "name", "matiere")}
        for m in data or []:
            nom = _champ(m, "nom", "name", "matiere")
            if not nom:
                continue
            coeff = _champ(m, "coefficient", "coef", default=1) or 1
            _upsert("matieres", "nom = ?", (nom,), ["coefficient"], [float(str(coeff).replace(",", ".").strip() or 1)])
            resultat["matieres"] += 1
        if noms_srv:
            _supprimer_absents("matieres", noms_srv, resultat, pends)
    except Exception as exc:
        resultat["erreurs"].append(f"matieres: {exc}")

    # ---------- Classes (rattachees aux cycles locaux par nom) ----------
    try:
        data, err = client.classes()
        if err:
            raise RuntimeError(err)
        noms_srv = {_champ(cl, "nom", "classe", "name")
                    for cl in data or [] if _champ(cl, "nom", "classe", "name")}
        for cl in data or []:
            nom = _champ(cl, "nom", "classe", "name")
            if not nom:
                continue
            cycle_local = None
            srv_cycle_id = _champ(cl, "cycle_id", "id_cycle")
            if srv_cycle_id is not None and srv_cycle_id in cycle_ids_srv:
                cycle_local = cycle_ids_srv[srv_cycle_id][1]
            elif srv_cycle_id is not None and cycles_srv:
                # Le cycle distant n'a pas pu etre mappe : chercher son nom.
                parent = next((c for c in cycles_srv if c.get("id") == srv_cycle_id), None)
                if parent:
                    nom_parent = _champ(parent, "nom", "name", "cycle")
                    ligne = db.query_one("SELECT id FROM cycles WHERE nom = ?", (nom_parent,))
                    cycle_local = ligne["id"] if ligne else None
            colonnes_classe = ["niveau", "capacite", "salle", "titulaire"]
            capacite_val = _champ(cl, "capacite", default=50) or 50
            try:
                capacite_val = int(float(str(capacite_val).replace(",", ".").strip() or 50))
            except (ValueError, TypeError):
                capacite_val = 50
            valeurs_classe = [_champ(cl, "niveau"),
                              capacite_val,
                              _champ(cl, "salle"),
                              _champ(cl, "titulaire")]
            if cycle_local is not None:
                # Le serveur a informe le cycle : on le synchronise. Sinon on
                # garde le lien local existant (pull partiel / cycle inconnu).
                colonnes_classe.append("cycle_id")
                valeurs_classe.append(cycle_local)
            _upsert("classes", "nom = ?", (nom,),
                    colonnes_classe, valeurs_classe)
            resultat["classes"] += 1
        if noms_srv and not resultat["erreurs"]:
            # On ne supprime une classe locale que si le pull des cycles a
            # deja reussi (le serveur a repondu completement).
            _supprimer_absents("classes", noms_srv, resultat, pends)
    except Exception as exc:
        resultat["erreurs"].append(f"classes: {exc}")

    # ---------- Annees scolaires (+ alignement de l'annee active) ----------
    annees_srv = []
    try:
        data, err = client.lister_annees_scolaires()
        if err:
            raise RuntimeError(err)
        annees_srv = data or []
        for a in annees_srv:
            libelle = _champ(a, "libelle", "annee_scolaire", "annee")
            if not libelle:
                continue
            _upsert(
                "annees_scolaires", "libelle = ?", (libelle,),
                ["date_debut", "date_fin"],
                [_champ(a, "date_debut", "debut"),
                 _champ(a, "date_fin", "fin")])
            resultat["annees"] += 1

        active, err = client.annee_scolaire_active()
        if not err and active:
            libelle_active = _champ(active, "libelle", "annee_scolaire", "annee")
            if libelle_active and db.query_one(
                    "SELECT id FROM annees_scolaires WHERE libelle = ? AND est_active = 0",
                    (libelle_active,)):
                # Un seul actif : on copie l'etat du serveur.
                db.execute("UPDATE annees_scolaires SET est_active = 0")
                db.execute(
                    "UPDATE annees_scolaires SET est_active = 1 WHERE libelle = ?",
                    (libelle_active,))
    except Exception as exc:
        resultat["erreurs"].append(f"annees: {exc}")

    # ---------- Tarifs (mirroir par classe resolue localement) ----------
    try:
        data, err = client.tarifs_scolarite()
        if err:
            raise RuntimeError(err)
        attendus = {}  # classe_nom -> {(type, annee): montant}
        for t in data or []:
            classe_nom = _champ(t, "classe_nom", "classe")
            if not classe_nom:
                continue
            entrees = attendus.setdefault(classe_nom, {})
            if _champ(t, "type_frais") is not None:
                entrees[(_champ(t, "type_frais"),
                         _champ(t, "annee_scolaire") or "")] = \
                    float(_champ(t, "montant", default=0) or 0)
            else:
                # Format serveur d'origine : inscription + pension.
                inscr = _champ(t, "frais_inscription")
                pension = _champ(t, "montant_pension")
                annee_srv = _champ(t, "annee_scolaire") or ""
                if inscr is not None:
                    entrees[("Inscription", annee_srv)] = float(inscr or 0)
                if pension is not None:
                    entrees[("Scolarite", annee_srv)] = float(pension or 0)

        for classe_nom, entrees in attendus.items():
            classe_loc = db.query_one(
                "SELECT id FROM classes WHERE nom = ?", (classe_nom,))
            if not classe_loc:
                continue
            classe_id = classe_loc["id"]
            existants = {
                (r["type_frais"], r.get("annee_scolaire") or ""): r["id"]
                for r in db.query(
                    "SELECT * FROM tarifs WHERE classe_id = ?", (classe_id,))
            }
            for (type_frais, annee), montant in entrees.items():
                if (type_frais, annee) in existants:
                    db.execute(
                        "UPDATE tarifs SET montant = ? WHERE id = ?",
                        (montant, existants[(type_frais, annee)]))
                else:
                    db.execute(
                        """INSERT INTO tarifs (classe_id, type_frais, montant, annee_scolaire)
                           VALUES (?, ?, ?, ?)""",
                        (classe_id, type_frais, montant, annee))
            # PAS DE MIROIR DESTRUCTEUR : le serveur ne sait representer que
            # pension/inscription (pas de type_frais). Supprimer les tarifs
            # locaux absents du serveur effacerait a chaque sync les types
            # annexes (Cantine, Transport, Tenues...) — perte de donnees
            # reelle pour toutes les classes. Les tarifs locaux sont donc
            # conserves ; une suppression volontaire sera possible quand le
            # serveur exposera type_frais.
            resultat["tarifs"] += len(entrees)
    except Exception as exc:
        resultat["erreurs"].append(f"tarifs: {exc}")

    return resultat


def _classe_id_par_nom(nom):
    if not nom:
        return None
    ligne = db.query_one("SELECT id FROM classes WHERE nom = ?", (nom,))
    return ligne["id"] if ligne else None


def _matiere_id_par_nom(nom):
    if not nom:
        return None
    ligne = db.query_one("SELECT id FROM matieres WHERE nom = ?", (nom,))
    return ligne["id"] if ligne else None


def _gen_matricule():
    """Matricule local unique pour un eleve rapatrie sans matricule serveur."""
    from datetime import date
    prefix = f"ELEV{date.today().year}"
    ligne = db.query_one(
        "SELECT MAX(CAST(SUBSTR(matricule, ?) AS INTEGER)) AS max_num"
        " FROM eleves WHERE matricule LIKE ?",
        (len(prefix) + 1, f"{prefix}%"))
    num = (ligne["max_num"] or 0) + 1
    return f"{prefix}{num:04d}"


def _eleve_id_local(serie, nom=None, prenom=None):
    """Resout l'eleve local par uuid_client, puis par (nom, prenom)."""
    uuid_client = serie.get("uuid_client") or serie.get("eleve_uuid")
    if uuid_client:
        ligne = db.query_one("SELECT id FROM eleves WHERE uuid_client = ?", (uuid_client,))
        if ligne:
            return ligne["id"]
    if nom and prenom:
        ligne = db.query_one(
            "SELECT id FROM eleves WHERE nom = ? AND prenom = ?",
            (nom, prenom))
        if ligne:
            return ligne["id"]
    return None


def pull_donnees():
    """Rapatrie les donnees d'action depuis le serveur (eleves, personnel,
    programmes, presences, notes, paiements).

    Principe : UPSERT par cles naturelles, jamais de suppression. Une ligne
    locale absente du serveur est conservee (l'upsert est purement additif).
    Chaque section est independante : un echec n'annule pas les autres.
    """
    from api import client

    resultat = {"eleves": 0, "personnel": 0, "programmes": 0,
                "presences": 0, "notes": 0, "paiements": 0,
                "suppressions": 0,
                "erreurs": []}

    # ---------- Eleves (classe resolue par nom) ----------
    try:
        data, err = client.eleves()
        if err:
            raise RuntimeError(err)
        for e in data or []:
            nom = _champ(e, "nom")
            prenom = _champ(e, "prenom")
            if not (nom or prenom):
                continue
            # Cle d'identite : uuid_client serveur. Une ligne locale creee
            # hors-ligne sans uuid est rattachee par (nom, prenom) ; sinon
            # l'eleve distant est cree localement (le pull est additif).
            uuid_client = _champ(e, "uuid_client") or str(uuid.uuid4())
            existant = db.query_one(
                "SELECT id, uuid_client FROM eleves WHERE uuid_client = ?",
                (uuid_client,))
            if not existant and nom and prenom:
                ligne_libre = db.query_one(
                    "SELECT id, uuid_client FROM eleves WHERE nom = ? AND prenom = ?"
                    " AND (uuid_client IS NULL OR uuid_client = '')",
                    (nom, prenom))
                if ligne_libre:
                    db.execute("UPDATE eleves SET uuid_client = ? WHERE id = ?",
                               (uuid_client, ligne_libre["id"]))
                    existant = ligne_libre
            if not existant:
                matricule = _champ(e, "matricule") or _gen_matricule()
                db.execute(
                    """INSERT INTO eleves (uuid_client, matricule, nom, prenom, sexe,
                                           date_naissance, lieu_naissance, adresse,
                                           redoublant, statut)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (uuid_client, matricule,
                     _champ(e, "nom"), _champ(e, "prenom"), _champ(e, "sexe"),
                     _champ(e, "date_naissance"), _champ(e, "lieu_naissance"),
                     _champ(e, "adresse"),
                     _bool_int(_champ(e, "redoublant", default=0)),
                     _statut_eleve_local(_champ(e, "statut"))))
                existant = db.query_one(
                    "SELECT id, uuid_client FROM eleves WHERE uuid_client = ?",
                    (uuid_client,))
                resultat["eleves"] += 1
            if not existant:
                continue
            colonnes = ["nom", "prenom", "sexe", "date_naissance", "lieu_naissance",
                        "adresse", "redoublant", "statut"]
            valeurs = [_champ(e, "nom"), _champ(e, "prenom"), _champ(e, "sexe"),
                       _champ(e, "date_naissance"), _champ(e, "lieu_naissance"),
                       _champ(e, "adresse"),
                       _bool_int(_champ(e, "redoublant", default=0)),
                       _statut_eleve_local(_champ(e, "statut"))]
            if _champ(e, "classe") is not None:
                classe_id = _classe_id_par_nom(_champ(e, "classe"))
                if classe_id:
                    colonnes.append("classe_id")
                    valeurs.append(classe_id)
            assignments = ", ".join(f"{c} = ?" for c in colonnes)
            db.execute(
                f"UPDATE eleves SET {assignments} WHERE id = ?",
                (*valeurs, existant["id"]))
            if not existant["uuid_client"]:
                db.execute(
                    "UPDATE eleves SET uuid_client = ? WHERE id = ?",
                    (uuid_client, existant["id"]))
    except Exception as exc:
        resultat["erreurs"].append(f"eleves: {exc}")

    # ---------- Tombstones eleves (suppressions server -> client) ----------
    try:
        data, err = client.eleves_supprimes_syndication()
        if not err and data:
            # Protection : si un eleve a ete cree hors-ligne et figure encore
            # dans la file PENDING (POST /eleve), on ne le supprime pas
            # localement — le push va le creer sur le serveur.
            uuids_pends = set()
            import json as _json
            try:
                for r in db.query(
                        "SELECT payload FROM file_attente_synchro WHERE status = 'PENDING'"
                        " AND method = 'POST' AND endpoint = '/eleve'"):
                    p = _json.loads(r["payload"])
                    if isinstance(p, dict) and p.get("uuid_client"):
                        uuids_pends.add(p["uuid_client"])
            except Exception:
                uuids_pends = set()
            for t in data:
                uuid_c = t.get("uuid_client")
                if not uuid_c or uuid_c in uuids_pends:
                    continue
                ligne = db.query_one(
                    "SELECT id FROM eleves WHERE uuid_client = ?", (uuid_c,))
                if not ligne:
                    continue
                eid = ligne["id"]
                with db.transaction() as txn:
                    txn.execute("DELETE FROM notes WHERE eleve_id = ?", (eid,))
                    txn.execute("DELETE FROM presences WHERE eleve_id = ?", (eid,))
                    txn.execute("DELETE FROM paiements WHERE eleve_id = ?", (eid,))
                    txn.execute("DELETE FROM eleves WHERE id = ?", (eid,))
                resultat["suppressions"] = resultat.get("suppressions", 0) + 1
    except Exception as exc:
        resultat["erreurs"].append(f"tombstones_eleves: {exc}")

    # ---------- Tombstones notes (suppressions server -> client) ----------
    try:
        data, err = client.notes_supprimes_syndication()
        if not err and data:
            uuids_pends = set()
            import json as _json
            try:
                for r in db.query(
                        "SELECT payload FROM file_attente_synchro WHERE status = 'PENDING'"
                        " AND method = 'POST' AND endpoint = '/note'"):
                    p = _json.loads(r["payload"])
                    if isinstance(p, dict) and p.get("uuid_client"):
                        uuids_pends.add(p["uuid_client"])
            except Exception:
                uuids_pends = set()
            for t in data:
                uuid_c = t.get("uuid_client")
                if not uuid_c or uuid_c in uuids_pends:
                    continue
                ligne = db.query_one(
                    "SELECT id FROM notes WHERE uuid_client = ?", (uuid_c,))
                if not ligne:
                    continue
                db.execute("DELETE FROM notes WHERE id = ?", (ligne["id"],))
                resultat["suppressions"] = resultat.get("suppressions", 0) + 1
    except Exception as exc:
        resultat["erreurs"].append(f"tombstones_notes: {exc}")

    # ---------- Tombstones paiements (suppressions server -> client) ----------
    try:
        data, err = client.paiements_supprimes_syndication()
        if not err and data:
            uuids_pends = set()
            import json as _json
            try:
                for r in db.query(
                        "SELECT payload FROM file_attente_synchro WHERE status = 'PENDING'"
                        " AND method = 'POST' AND endpoint = '/paiement'"):
                    p = _json.loads(r["payload"])
                    if isinstance(p, dict) and p.get("uuid_client"):
                        uuids_pends.add(p["uuid_client"])
            except Exception:
                uuids_pends = set()
            for t in data:
                uuid_c = t.get("uuid_client")
                if not uuid_c or uuid_c in uuids_pends:
                    continue
                ligne = db.query_one(
                    "SELECT id FROM paiements WHERE uuid_client = ?", (uuid_c,))
                if not ligne:
                    continue
                pid = ligne["id"]
                with db.transaction() as txn:
                    txn.execute("DELETE FROM paiements WHERE id = ?", (pid,))
                    txn.execute("DELETE FROM transactions WHERE paiement_id = ?", (pid,))
                resultat["suppressions"] = resultat.get("suppressions", 0) + 1
    except Exception as exc:
        resultat["erreurs"].append(f"tombstones_paiements: {exc}")

    # ---------- Tombstones presences (suppressions server -> client) ----------
    try:
        data, err = client.presences_supprimes_syndication()
        if not err and data:
            uuids_pends = set()
            import json as _json
            try:
                for r in db.query(
                        "SELECT payload FROM file_attente_synchro WHERE status = 'PENDING'"
                        " AND method = 'POST' AND endpoint = '/presence'"):
                    p = _json.loads(r["payload"])
                    if isinstance(p, dict) and p.get("uuid_client"):
                        uuids_pends.add(p["uuid_client"])
            except Exception:
                uuids_pends = set()
            for t in data:
                uuid_c = t.get("uuid_client")
                if not uuid_c or uuid_c in uuids_pends:
                    continue
                ligne = db.query_one(
                    "SELECT id FROM presences WHERE uuid_client = ?", (uuid_c,))
                if not ligne:
                    continue
                db.execute("DELETE FROM presences WHERE id = ?", (ligne["id"],))
                resultat["suppressions"] = resultat.get("suppressions", 0) + 1
    except Exception as exc:
        resultat["erreurs"].append(f"tombstones_presences: {exc}")

    # ---------- Personnel (enseignants, par nom_complet) ----------
    try:
        data, err = client.enseignants()
        if err:
            raise RuntimeError(err)
        for p in data or []:
            nom = _champ(p, "nom")
            prenom = _champ(p, "prenom")
            if not nom:
                continue
            nom_complet = " ".join(x for x in (nom, prenom) if x)
            _upsert(
                "personnel", "nom_complet = ?", (nom_complet,),
                ["nom_complet", "telephone", "email", "statut"],
                [nom_complet, _champ(p, "telephone"), _champ(p, "email"),
                 _champ(p, "statut", default="Actif")])
            resultat["personnel"] += 1
    except Exception as exc:
        resultat["erreurs"].append(f"personnel: {exc}")

    # ---------- Programmes (par classe + matiere resolvee localement) ----------
    try:
        data, err = client.tous_les_programme()
        if err:
            raise RuntimeError(err)
        for pr in data or []:
            classe_id = _classe_id_par_nom(_champ(pr, "classe_nom", "classe"))
            matiere_id = _matiere_id_par_nom(_champ(pr, "matiere_nom", "matiere"))
            if not classe_id or not matiere_id:
                continue
            enseignant_id = None
            enseignant_nom = _champ(pr, "enseignant_nom")
            if enseignant_nom:
                ligne = db.query_one(
                    "SELECT id FROM personnel WHERE nom_complet LIKE ?",
                    (f"{enseignant_nom}%",))
                if ligne:
                    enseignant_id = ligne["id"]
            existant = db.query_one(
                "SELECT id FROM programmes WHERE classe_id = ? AND matiere_id = ?",
                (classe_id, matiere_id))
            if existant:
                db.execute(
                    "UPDATE programmes SET enseignant_id = ?, coefficient = ? WHERE id = ?",
                    (enseignant_id, _coef_float(
                        _champ(pr, "coefficient", default=1)), existant["id"]))
            else:
                db.execute(
                    """INSERT INTO programmes (classe_id, matiere_id, enseignant_id, coefficient)
                       VALUES (?, ?, ?, ?)""",
                    (classe_id, matiere_id, enseignant_id,
                     _coef_float(_champ(pr, "coefficient", default=1))))
            resultat["programmes"] += 1
    except Exception as exc:
        resultat["erreurs"].append(f"programmes: {exc}")

    # ---------- Presences (par eleve_uuid + date) ----------
    try:
        data, err = client.toutes_presence()
        if err:
            raise RuntimeError(err)
        for p in data or []:
            eleve_id = _eleve_id_local(p, _champ(p, "nom"), _champ(p, "prenom"))
            date_presence = _champ(p, "date_presence", "date")
            if not eleve_id or not date_presence:
                continue
            date = str(date_presence)[:10]
            existant = db.query_one(
                "SELECT id FROM presences WHERE eleve_id = ? AND date = ?",
                (eleve_id, date))
            statut = _champ(p, "statut", default="Present")
            motif = _champ(p, "motif") or _champ(p, "justifie")
            if existant:
                db.execute(
                    "UPDATE presences SET statut = ?, motif = ? WHERE id = ?",
                    (statut, motif, existant["id"]))
            else:
                classe_id = db.query_one(
                    "SELECT classe_id FROM eleves WHERE id = ?", (eleve_id,))
                db.execute(
                    """INSERT INTO presences (eleve_id, classe_id, date, statut, motif)
                       VALUES (?, ?, ?, ?, ?)""",
                    (eleve_id, classe_id["classe_id"] if classe_id else None,
                     date, statut, motif))
            resultat["presences"] += 1
    except Exception as exc:
        resultat["erreurs"].append(f"presences: {exc}")

    # ---------- Notes (agregees par eleve + matiere + periode) ----------
    try:
        data, err = client.note_syndication()
        if err:
            raise RuntimeError(err)
        for n in data or []:
            eleve_id = _eleve_id_local(n, _champ(n, "nom"), _champ(n, "prenom"))
            matiere_id = _matiere_id_par_nom(_champ(n, "matiere_nom"))
            if not eleve_id or not matiere_id:
                continue
            periode = _champ(n, "trimestre", default="1er Trimestre")
            type_eval = str(_champ(n, "type_evaluation", default="") or "").lower()
            if "devoir" in type_eval and "1" in type_eval:
                champ = "devoir1"
            elif "devoir" in type_eval and "2" in type_eval:
                champ = "devoir2"
            elif "composition" in type_eval:
                champ = "composition"
            else:
                champ = "devoir1"
            val = _champ(n, "note")
            if val is None:
                continue
            existant = db.query_one(
                "SELECT id, devoir1, devoir2, composition FROM notes "
                "WHERE eleve_id = ? AND matiere_id = ? AND periode = ?",
                (eleve_id, matiere_id, periode))
            if existant:
                actuel = dict(existant)
                if actuel.get(champ) in (None, ""):
                    db.execute(
                        f"UPDATE notes SET {champ} = ? WHERE id = ?",
                        (val, existant["id"]))
            else:
                db.execute(
                    """INSERT INTO notes (eleve_id, matiere_id, periode, devoir1, devoir2, composition)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (eleve_id, matiere_id, periode,
                     val if champ == "devoir1" else None,
                     val if champ == "devoir2" else None,
                     val if champ == "composition" else None))
            resultat["notes"] += 1
    except Exception as exc:
        resultat["erreurs"].append(f"notes: {exc}")

    # ---------- Paiements (par eleve + montant + type_frais + trimestre) ----------
    try:
        data, err = client.paiement_syndication()
        if err:
            raise RuntimeError(err)
        for p in data or []:
            eleve_id = _eleve_id_local(p, _champ(p, "nom"), _champ(p, "prenom"))
            if not eleve_id:
                continue
            montant = _coef_float(_champ(p, "montant", default=0))
            type_frais = _champ(p, "type_frais", default="Scolarite")
            trimestre = _champ(p, "trimestre", default="")
            date_paiement = _champ(p, "date_paiement", default="")
            annee_scolaire = _champ(p, "annee_scolaire") or ""
            mode = _champ(p, "mode_paiement", "mode_reglement")

            # Dedup precise : on prefere la date (2 paiements legitimes du meme
            # montant/type a des dates differentes sont DISTINCTS).
            date_locale = (str(date_paiement)[:10] if date_paiement else None)
            if date_locale:
                existant = db.query_one(
                    """SELECT id FROM paiements
                       WHERE eleve_id = ? AND montant = ? AND type_frais = ?
                         AND date_paiement = ?""",
                    (eleve_id, montant, type_frais, date_locale))
            else:
                # Sans date, on retombe sur (eleve, montant, type, trimestre) :
                # risque d'ecrasement, mais c'est le seul rapprochement possible.
                existant = db.query_one(
                    """SELECT id FROM paiements
                       WHERE eleve_id = ? AND montant = ? AND type_frais = ?
                         AND (trimestre = ? OR (trimestre IS NULL AND ? = ''))""",
                    (eleve_id, montant, type_frais, trimestre, trimestre))
            if existant:
                db.execute(
                    "UPDATE paiements SET mode_reglement = ? WHERE id = ?",
                    (mode, existant["id"]))
            else:
                db.execute(
                    """INSERT INTO paiements (eleve_id, montant, mode_reglement,
                                              type_frais, date_paiement, annee_scolaire, trimestre)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (eleve_id, montant, mode, type_frais, date_locale,
                     annee_scolaire, trimestre))
            resultat["paiements"] += 1
    except Exception as exc:
        resultat["erreurs"].append(f"paiements: {exc}")

    # La Caisse ne lit que la table locale `transactions` : on cree les
    # ecritures manquantes pour les paiements rapatries (idempotent), sinon
    # des encaissements visibles dans Paiements seraient absents de la Caisse.
    try:
        from repositories.finance_repository import FinanceRepository
        FinanceRepository().reconcilier_caisse()
    except Exception as exc:
        resultat["erreurs"].append(f"reconciliation_caisse: {exc}")

    return resultat


def pull_comptes():
    """Rapatrie les comptes utilisateurs depuis le serveur.

    Upsert par username (identifiant serveur) : si le compte existe deja
    localement, seuls les champs metadata sont mis a jour (nom, email,
    telephone, role, actif) — le mot de passe n'est JAMAIS ecrase pour
    preserver le hash local. Si le compte est nouveau, il est cree avec le
    hash du serveur, ce qui permet le login multi-poste.
    Jamais destructif.
    """
    from api import client

    resultat = {"ajoutes": 0, "mis_a_jour": 0, "erreurs": []}

    try:
        data, err = client.comptes_syndication()
        if err:
            raise RuntimeError(err)
        for c in data or []:
            nom = _champ(c, "nom") or ""
            prenom = _champ(c, "prenom") or ""
            username = (_champ(c, "identifiant")
                        or (_champ(c, "email").split("@")[0]
                            if _champ(c, "email") else "")
                        or f"{nom.lower()}.{prenom.lower()}".strip("."))
            if not username:
                continue
            password = _champ(c, "mot_de_passe") or ""
            role = (_champ(c, "role") or "gestionnaire").lower()
            if role not in ("directeur", "gestionnaire"):
                role = "gestionnaire"
            statut_brut = _champ(c, "statut")
            actif = 1 if (statut_brut is None or _bool_int(statut_brut)
                          or str(statut_brut).strip().lower()
                          in ("actif", "active", "oui", "vrai", "yes")) else 0
            nom_complet = f"{nom} {prenom}".strip()
            telephone = _champ(c, "telephone")
            email = _champ(c, "email")
            existant = db.query_one(
                "SELECT id FROM utilisateurs WHERE username = ?", (username,))
            if existant:
                db.execute(
                    "UPDATE utilisateurs SET nom_complet=?, email=?, telephone=?, "
                    "role=?, actif=? WHERE id=?",
                    (nom_complet, email, telephone, role, actif, existant["id"]))
                resultat["mis_a_jour"] += 1
            else:
                if not password:
                    continue
                db.execute(
                    """INSERT INTO utilisateurs (nom_complet, username, email,
                                                telephone, password, role, actif)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (nom_complet, username, email, telephone, password, role, actif))
                resultat["ajoutes"] += 1
    except Exception as exc:
        resultat["erreurs"].append(f"comptes: {exc}")

    return resultat


def synchroniser_maintenant() -> dict:
    """« Synchroniser maintenant » : pull complet PUIS vidage de la file.

    Ordre volontaire : on recupere d'abord la structure et les donnees du
    serveur, pour que les ecritures en file (dependantes des references
    serveur) deviennent envoiables dans le meme passage. Chaque etape est
    independante — un echec n'annule pas les autres.
    """
    from api import api_disponible
    from api.sync_worker import vider_file_attente

    resultat = {"structure": 0, "donnees": 0, "comptes": 0,
                "envoyes": 0, "erreurs": []}
    if not api_disponible(force=True):
        resultat["erreurs"].append(
            "Serveur injoignable : rien a synchroniser maintenant.")
        return resultat

    for nom, fonction in (("structure", pull_structure),
                          ("donnees", pull_donnees),
                          ("comptes", pull_comptes)):
        try:
            compte = fonction() or {}
            resultat[nom] = sum(
                v for k, v in compte.items()
                if isinstance(v, int) and k not in ("erreurs",))
        except Exception as exc:
            resultat["erreurs"].append(f"{nom}: {exc}")

    try:
        resultat["envoyes"] = vider_file_attente()
    except Exception as exc:
        resultat["erreurs"].append(f"envoi: {exc}")

    return resultat
