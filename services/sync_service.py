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

from database import db


def _champ(row, *aliases, default=None):
    for cle in aliases:
        if cle in row and row[cle] is not None:
            return row[cle]
    return default


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


def _supprimer_absents(table, noms_srv, resultat):
    """Propage les suppressions faites sur le serveur, SANS risque :
    une ligne locale absente du serveur n'est supprimee que si aucune
    donnee locale ne en depend (sinon elle est conservee et signalee)."""
    gardes = []
    if table == "cycles":
        locaux = db.query("SELECT id, nom FROM cycles")
        for r in locaux:
            if r["nom"] in noms_srv:
                continue
            if db.query_one(
                    "SELECT id FROM classes WHERE cycle_id = ? LIMIT 1",
                    (r["id"],)):
                gardes.append(r["nom"])
                continue
            db.execute("DELETE FROM cycles WHERE id = ?", (r["id"],))
            resultat["suppressions"] += 1
    elif table == "matieres":
        locaux = db.query("SELECT id, nom FROM matieres")
        for r in locaux:
            if r["nom"] in noms_srv:
                continue
            if db.query_one(
                    "SELECT id FROM programmes WHERE matiere_id = ? LIMIT 1",
                    (r["id"],)):
                gardes.append(r["nom"])
                continue
            db.execute("DELETE FROM matieres WHERE id = ?", (r["id"],))
            resultat["suppressions"] += 1
    elif table == "classes":
        locaux = db.query("SELECT id, nom FROM classes")
        for r in locaux:
            if r["nom"] in noms_srv:
                continue
            depend = db.query_one(
                """SELECT e.id FROM eleves e WHERE e.classe_id = ?
                   UNION ALL SELECT t.id FROM tarifs t WHERE t.classe_id = ?
                   UNION ALL SELECT p.id FROM planning p WHERE p.classe_id = ?
                   UNION ALL SELECT pr.id FROM programmes pr WHERE pr.classe_id = ?
                   LIMIT 1""",
                (r["id"], r["id"], r["id"], r["id"]))
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
            _supprimer_absents("cycles", noms_cycles_srv, resultat)
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
            _upsert("matieres", "nom = ?", (nom,), ["coefficient"], [float(coeff)])
            resultat["matieres"] += 1
        if noms_srv:
            _supprimer_absents("matieres", noms_srv, resultat)
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
            _upsert(
                "classes", "nom = ?", (nom,),
                ["niveau", "capacite", "salle", "titulaire", "cycle_id"],
                [_champ(cl, "niveau"),
                 int(_champ(cl, "capacite", default=50) or 50),
                 _champ(cl, "salle"),
                 _champ(cl, "titulaire"),
                 cycle_local])
            resultat["classes"] += 1
        if noms_srv and not resultat["erreurs"]:
            # On ne supprime une classe locale que si le pull des cycles a
            # deja reussi (le serveur a repondu completement).
            _supprimer_absents("classes", noms_srv, resultat)
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
            # Mirroir : retirer les tarifs locaux absents du serveur.
            pour_supprimer = [tid for cle, tid in existants.items()
                              if cle not in entrees]
            for tid in pour_supprimer:
                db.execute("DELETE FROM tarifs WHERE id = ?", (tid,))
            resultat["tarifs"] += len(entrees)
    except Exception as exc:
        resultat["erreurs"].append(f"tarifs: {exc}")

    return resultat
