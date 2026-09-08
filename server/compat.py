"""
Couche de compatibilite entre l'application de bureau (client de synchronisation)
et l'API FastAPI du serveur.

Cette couche enregistre des routes supplementaires AVANT les routes historiques
du serveur. Elle accepte les charges utiles (payloads) de l'application de bureau
et les traduit vers le schema MySQL du serveur, sans modifier le comportement
des routes existantes pour leurs consommateurs actuels.
"""

import os
import random
import string
from datetime import date, datetime

from fastapi import Body, Header, HTTPException, Path

try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None

import securite

try:
    import mysql.connector
except ImportError:  # pragma: no cover - dependance optionnelle a l'import
    mysql_connector_disponible = False
    mysql = None
else:
    mysql_connector_disponible = True


# ============================================================
# CONFIGURATION BASE DE DONNEES (meme valeurs par defaut que main.py)
# ============================================================

def _parametre_bd(nom, defaut):
    return os.environ.get(nom, defaut)


def connexion():
    # Mode "sans installation" : fichier SQLite, aucun MySQL requis.
    if os.environ.get("GS_DB_MODE", "").strip().lower() == "sqlite":
        try:
            from server.sqlite_backend import connexion_sqlite
        except ImportError:
            from sqlite_backend import connexion_sqlite
        return connexion_sqlite()
    if not mysql_connector_disponible:
        raise HTTPException(status_code=500, detail="mysql-connector-python non installe")
    return mysql.connector.connect(
        host=_parametre_bd("GS_DB_HOST", "localhost"),
        user=_parametre_bd("GS_DB_USER", "root"),
        password=_parametre_bd("GS_DB_PASSWORD", ""),
        database=_parametre_bd("GS_DB_NAME", "ecole"),
    )


# ============================================================
# PISTE D'AUDIT
# ============================================================

def _identite_depuis_token(authorization):
    """Decode l'entete Authorization: Bearer <jwt> et retourne le payload.

    Leve 401 si l'entete est absente, mal formee ou si le token est
    invalide/expire.
    """
    if jwt is None:
        raise HTTPException(status_code=500, detail="PyJWT non installe")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401,
                            detail="En-tête Authorization manquant")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return jwt.decode(token, securite.SECRET_KEY,
                          algorithms=[securite.ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


def enregistrer_audit(curseur, utilisateur_id, action, details="", adresse_ip=None):
    """Insere une entree dans la piste d'audit.

    Appelée avec le curseur de la transaction en cours : l'entree d'audit
    est validee (commit) atomiquement avec l'operation qu'elle decrit.
    """
    curseur.execute(
        "INSERT INTO audit_log (utilisateur_id, action, details, adresse_ip)"
        " VALUES (%s, %s, %s, %s)",
        (
            utilisateur_id,
            str(action)[:80],
            str(details or "")[:500],
            adresse_ip,
        ),
    )


# ============================================================
# TABLES COMPLEMENTAIRES (parametres locaux, planning, caisse)
# ============================================================

TABLES_COMPLEMENTAIRES = """
CREATE TABLE IF NOT EXISTS parametre (
    cle VARCHAR(100) PRIMARY KEY,
    valeur TEXT
);

CREATE TABLE IF NOT EXISTS planning (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT NOT NULL,
    jour VARCHAR(20) NOT NULL,
    creneau VARCHAR(30) NOT NULL,
    matiere VARCHAR(100),
    salle VARCHAR(50),
    FOREIGN KEY (classe_id) REFERENCES classe(id)
);

CREATE TABLE IF NOT EXISTS caisse_transaction (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reference VARCHAR(30),
    beneficiaire VARCHAR(150),
    motif VARCHAR(255),
    categorie VARCHAR(80),
    montant DECIMAL(12,2) NOT NULL,
    type ENUM('entree', 'sortie') NOT NULL,
    mode_reglement VARCHAR(30),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    utilisateur_id INT,
    action VARCHAR(80) NOT NULL,
    details VARCHAR(500),
    adresse_ip VARCHAR(45),
    INDEX idx_audit_action (action),
    INDEX idx_audit_date (horodatage)
);
"""


def creer_tables_complementaires(cursor):
    """Cree les tables additionnelles si necessaire (ignore si deja la)."""
    for instruction in TABLES_COMPLEMENTAIRES.split(";"):
        lignes = [l for l in instruction.strip().split("\n")
                  if l.strip() and not l.strip().startswith("--")]
        if not lignes:
            continue
        try:
            cursor.execute("\n".join(lignes))
        except Exception:
            pass


# ============================================================
# UTILITAIRES DE NORMALISATION
# ============================================================

def _chaine(valeur, defaut=""):
    if valeur is None:
        return defaut
    texte = str(valeur).strip()
    return texte if texte else defaut


def _premier(*valeurs, defaut=None):
    for v in valeurs:
        if v is not None and str(v).strip() != "":
            return v
    return defaut


def _sexe(valeur):
    s = _chaine(valeur, "M").upper()
    return "F" if s.startswith("F") else "M"


def _redoublant(valeur):
    if isinstance(valeur, bool):
        return "1" if valeur else "0"
    s = _chaine(valeur, "0").lower()
    return "1" if s in ("1", "true", "oui", "oui", "y", "yes") else "0"


_STATUTS_ELEVE = ("actif", "inactif", "exclu")


def _statut_eleve(valeur):
    s = _chaine(valeur, "actif").lower()
    if s in _STATUTS_ELEVE:
        return s
    correspondance = {
        "inscrit": "actif", "en règle": "actif", "en regle": "actif",
        "radié": "exclu", "radie": "exclu", "exclus": "exclu",
        "suspendu": "inactif", "abandon": "inactif",
    }
    return correspondance.get(s, "actif")


def _statut_enseignant(valeur):
    """Traduit le statut métier d'un enseignant vers l'ENUM MySQL
    ('actif'/'inactif') : le bureau envoie « Enseignant »/« Professeur »,
    MySQL n'accepte que les valeurs de l'ENUM."""
    s = _chaine(valeur, "actif").lower()
    if s in ("actif", "inactif"):
        return s
    correspondance = {
        "enseignant": "actif", "enseignants": "actif", "professeur": "actif",
        "professeurs": "actif", "surveillant": "actif", "surveillants": "actif",
        "vacataire": "actif", "stagiare": "actif", "stagiaire": "actif",
        "congé": "inactif", "conge": "inactif", "en congé": "inactif",
        "inactif": "inactif", "suspendu": "inactif", "licencié": "inactif",
        "licencie": "inactif",
    }
    return correspondance.get(s, "actif")


def _date_sql(valeur, defaut=None):
    """Convertit une date heterogene en chaine YYYY-MM-DD."""
    if isinstance(valeur, (date, datetime)):
        return valeur.strftime("%Y-%m-%d")
    s = _chaine(valeur)
    if not s:
        return defaut
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:19] if "T" in s or " " in s else s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return defaut


_TRIMESTRES = {
    "t1": "T1", "1": "T1", "1er": "T1", "1er trimestre": "T1", "trim 1": "T1", "trimestre 1": "T1",
    "t2": "T2", "2": "T2", "2e": "T2", "2eme": "T2", "2ème": "T2",
    "2e trimestre": "T2", "2ème trimestre": "T2", "trim 2": "T2", "trimestre 2": "T2",
    "t3": "T3", "3": "T3", "3e": "T3", "3eme": "T3", "3ème": "T3",
    "3e trimestre": "T3", "3ème trimestre": "T3", "trim 3": "T3", "trimestre 3": "T3",
}


def _trimestre(valeur):
    s = _chaine(valeur).lower()
    return _TRIMESTRES.get(s)


_TYPES_FRAIS = ("inscription", "scolarite", "scolarité", "cantine", "transport")


def _type_frais(valeur):
    s = _chaine(valeur, "Scolarite").lower()
    if s == "scolarité":
        return "Scolarite"
    if s in _TYPES_FRAIS:
        return s.capitalize()
    return "Scolarite"


_MODES_PAIEMENT = {
    "espece": "espece", "espèces": "espece", "especes": "espece",
    "cash": "espece", "virement": "virement", "mobile money": "mobile_money",
    "mobile_money": "mobile_money", "mobile": "mobile_money", "momo": "mobile_money",
    "cheque": "cheque", "chèque": "cheque",
}


def _mode_paiement(valeur):
    return _MODES_PAIEMENT.get(_chaine(valeur, "espece").lower(), "espece")


_STATUTS_PRESENCE = {
    "present": "Present", "présent": "Present", "p": "Present",
    "absent": "Absent", "a": "Absent",
    "en retard": "En retard", "retard": "En retard", "r": "En retard",
}


def _statut_presence(valeur):
    s = _chaine(valeur, "Present").lower()
    return _STATUTS_PRESENCE.get(s, "Present")


def _normaliser_eleve(donnees):
    """Traduit un dictionnaire d'eleve de l'application de bureau vers le
    schema du serveur (colonnes de la table eleve)."""
    return {
        "nom": _chaine(donnees.get("nom"), "-"),
        "prenom": _chaine(donnees.get("prenom"), "-"),
        "sexe": _sexe(donnees.get("sexe")),
        "date_naissance": _date_sql(donnees.get("date_naissance")),
        "lieu_naissance": _chaine(donnees.get("lieu_naissance"), "-"),
        "adresse": _chaine(_premier(donnees.get("adresse"), donnees.get("quartier")), "-"),
        "nom_parent": _chaine(_premier(
            donnees.get("nom_parent"), donnees.get("pere_nom"),
            donnees.get("tuteur_nom"), donnees.get("mere_nom")), "-"),
        "numero_parent": _chaine(_premier(
            donnees.get("telephone_parent"), donnees.get("numero_parent"),
            donnees.get("pere_tel"), donnees.get("mere_tel"),
            donnees.get("tuteur_tel"))),
        "redoublant": _redoublant(_premier(donnees.get("redoublant"), 0)),
        "statut": _statut_eleve(donnees.get("statut")),
    }


def _id_entier(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def _annee_scolaire_active(cursor):
    cursor.execute("SELECT id FROM annee_scolaire WHERE est_active = TRUE LIMIT 1")
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


def _derniere_inscription(cursor, eleve_id, classe_id=None):
    sql = "SELECT id FROM inscription WHERE eleve_id = %s"
    params = [eleve_id]
    if classe_id is not None:
        sql += " AND classe_id = %s"
        params.append(classe_id)
    sql += " ORDER BY id DESC LIMIT 1"
    cursor.execute(sql, tuple(params))
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


def _token_aleatoire(longueur=24):
    caracteres = string.ascii_letters + string.digits
    return "".join(random.SystemRandom().choice(caracteres) for _ in range(longueur))


# ============================================================
# HELPERS : ELEVES
# ============================================================

def _creer_eleve_complet(payload_brut: dict):
    """POST /eleve : accepte la forme enveloppee {uuid_client, eleve, paiement}
    OU la forme plate de l'application de bureau."""
    if not isinstance(payload_brut, dict):
        raise HTTPException(status_code=400, detail="Corps JSON invalide")

    enveloppe = isinstance(payload_brut.get("eleve"), dict)
    brut_eleve = payload_brut["eleve"] if enveloppe else payload_brut
    brut_paiement = payload_brut.get("paiement") if enveloppe else None
    uuid_client = _chaine(_premier(
        payload_brut.get("uuid_client"), brut_eleve.get("uuid_client"))) or None

    eleve = _normaliser_eleve(brut_eleve)
    classe_id = _id_entier(brut_eleve.get("classe_id"))

    conn = connexion()
    curseur = conn.cursor()
    try:
        # Anti-doublon hors-ligne (meme logique que POST /ajout_eleve)
        if uuid_client:
            curseur.execute("SELECT id FROM eleve WHERE uuid_client = %s", (uuid_client,))
            existant = curseur.fetchone()
            if existant:
                conn.commit()
                return {"message": "Élève déjà enregistré (synchronisé)",
                        "eleve_id": existant[0]}

        curseur.execute(
            """INSERT INTO eleve (nom, prenom, sexe, date_naissance, lieu_naissance,
               adresse, nom_parent, redoublant, statut, numero_parent, uuid_client)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (eleve["nom"], eleve["prenom"], eleve["sexe"], eleve["date_naissance"],
             eleve["lieu_naissance"], eleve["adresse"], eleve["nom_parent"],
             eleve["redoublant"], eleve["statut"], eleve["numero_parent"], uuid_client),
        )
        eleve_id = curseur.lastrowid

        inscription_id = None
        if classe_id is not None:
            annee_id = _annee_scolaire_active(curseur)
            if annee_id:
                curseur.execute(
                    "INSERT INTO inscription (eleve_id, classe_id, annee_scolaire_id)"
                    " VALUES (%s, %s, %s)", (eleve_id, classe_id, annee_id))
                inscription_id = curseur.lastrowid

                if brut_paiement:
                    curseur.execute(
                        """INSERT INTO paiement (inscription_id, type_frais, montant,
                           mode_paiement, trimestre, mois, uuid_client)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (inscription_id,
                         _type_frais(brut_paiement.get("type_frais")),
                         float(brut_paiement.get("montant") or 0),
                         _mode_paiement(brut_paiement.get("mode_paiement")),
                         _trimestre(brut_paiement.get("trimestre")),
                         _chaine(brut_paiement.get("mois")) or None,
                         _chaine(brut_paiement.get("uuid_client")) or None))

        conn.commit()
        reponse = {"message": "Élève enregistré avec succès", "eleve_id": eleve_id}
        if inscription_id:
            reponse["inscription_id"] = inscription_id
        return reponse
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement élève : {exc}")
    finally:
        curseur.close()
        conn.close()


_COLONNES_ELEVE_MODIFIABLES = (
    "nom", "prenom", "sexe", "date_naissance", "lieu_naissance", "adresse",
    "nom_parent", "redoublant", "statut", "numero_parent",
)


def _modifier_eleve(eleve_id: int, payload_brut: dict):
    if not isinstance(payload_brut, dict):
        raise HTTPException(status_code=400, detail="Corps JSON invalide")
    brut = payload_brut.get("eleve") if isinstance(payload_brut.get("eleve"), dict) else payload_brut
    eleve = _normaliser_eleve(brut)

    sources_nom_parent = ("nom_parent", "pere_nom", "tuteur_nom", "mere_nom")
    sources_numero_parent = ("telephone_parent", "numero_parent",
                             "pere_tel", "mere_tel", "tuteur_tel")

    champs = {}
    for colonne in _COLONNES_ELEVE_MODIFIABLES:
        if brut.get(colonne) is not None:
            champs[colonne] = eleve[colonne]
    if "nom_parent" not in champs and any(brut.get(s) for s in sources_nom_parent):
        champs["nom_parent"] = eleve["nom_parent"]
    if "numero_parent" not in champs and any(brut.get(s) for s in sources_numero_parent):
        champs["numero_parent"] = eleve["numero_parent"]
    classe_id = _id_entier(brut.get("classe_id"))

    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("SELECT id FROM eleve WHERE id = %s", (eleve_id,))
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Élève non trouvé")

        if champs:
            affectations = ", ".join(f"{c} = %s" for c in champs)
            curseur.execute(f"UPDATE eleve SET {affectations} WHERE id = %s",
                            (*champs.values(), eleve_id))

        if classe_id is not None:
            inscription_id = _derniere_inscription(curseur, eleve_id)
            if inscription_id:
                curseur.execute("UPDATE inscription SET classe_id = %s WHERE id = %s",
                                (classe_id, inscription_id))
            else:
                annee_id = _annee_scolaire_active(curseur)
                if annee_id:
                    curseur.execute(
                        "INSERT INTO inscription (eleve_id, classe_id, annee_scolaire_id)"
                        " VALUES (%s, %s, %s)", (eleve_id, classe_id, annee_id))
        enregistrer_audit(curseur, None, "modification_eleve",
                          f"eleve_id={eleve_id} champs={sorted(champs)}")
        conn.commit()
        return {"message": "Élève modifié avec succès", "eleve_id": eleve_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification élève : {exc}")
    finally:
        curseur.close()
        conn.close()


def _vider_donnees_eleve(eleve_id: int, table: str):
    conn = connexion()
    curseur = conn.cursor()
    try:
        if table == "presences":
            curseur.execute("DELETE FROM presences WHERE eleve_id = %s", (eleve_id,))
        elif table == "note":
            curseur.execute(
                """DELETE FROM note WHERE inscription_id IN
                   (SELECT id FROM inscription WHERE eleve_id = %s)""", (eleve_id,))
        elif table == "paiement":
            curseur.execute(
                """DELETE FROM paiement WHERE inscription_id IN
                   (SELECT id FROM inscription WHERE eleve_id = %s)""", (eleve_id,))
        else:
            raise HTTPException(status_code=400, detail="Table inconnue")
        enregistrer_audit(curseur, None, "suppression_donnees_eleve",
                          f"eleve_id={eleve_id} table={table}")
        conn.commit()
        return {"message": f"Données '{table}' supprimées"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur suppression : {exc}")
    finally:
        curseur.close()
        conn.close()


# ============================================================
# HELPERS : CLASSES / CYCLES / MATIERES / PROGRAMMES
# ============================================================

def _creer_classe(payload: dict):
    nom = _chaine(_premier(payload.get("nom"), payload.get("classe")))
    cycle_id = _id_entier(payload.get("cycle_id"))
    if not nom:
        raise HTTPException(status_code=400, detail="Le nom de la classe est obligatoire")
    if cycle_id is None:
        raise HTTPException(status_code=400, detail="cycle_id obligatoire")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("INSERT INTO classe (classe, cycle_id) VALUES (%s, %s)",
                        (nom, cycle_id))
        conn.commit()
        return {"message": "Classe ajoutée avec succès", "id": curseur.lastrowid}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur ajout classe : {exc}")
    finally:
        curseur.close()
        conn.close()


def _modifier_classe(classe_id: int, payload: dict):
    champs = {}
    nom = _premier(payload.get("nom"), payload.get("classe"))
    if nom:
        champs["classe"] = _chaine(nom)
    if payload.get("cycle_id") is not None:
        champs["cycle_id"] = _id_entier(payload.get("cycle_id"))
    if not champs:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    conn = connexion()
    curseur = conn.cursor()
    try:
        affectations = ", ".join(f"{c} = %s" for c in champs)
        curseur.execute(f"UPDATE classe SET {affectations} WHERE id = %s",
                        (*champs.values(), classe_id))
        conn.commit()
        return {"message": "Classe mise à jour avec succès !",
                "champs_modifies": champs}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification classe : {exc}")
    finally:
        curseur.close()
        conn.close()


def _supprimer_classe(ref: str):
    conn = connexion()
    curseur = conn.cursor()
    try:
        identifiant = _id_entier(ref)
        if identifiant is not None:
            curseur.execute("SELECT id FROM classe WHERE id = %s", (identifiant,))
        else:
            curseur.execute("SELECT id FROM classe WHERE classe = %s", (ref,))
        ligne = curseur.fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail="Classe non trouvée")
        id_classe = ligne[0]
        curseur.execute("DELETE FROM programme WHERE classe_id = %s", (id_classe,))
        curseur.execute("DELETE FROM tarif_scolarite WHERE classe_id = %s", (id_classe,))
        curseur.execute("DELETE FROM inscription WHERE classe_id = %s", (id_classe,))
        curseur.execute("DELETE FROM planning WHERE classe_id = %s", (id_classe,))
        curseur.execute("UPDATE eleve JOIN inscription i ON i.eleve_id = eleve.id"
                        " SET eleve.est_supprime = TRUE WHERE i.classe_id = %s", (id_classe,))
        curseur.execute("DELETE FROM classe WHERE id = %s", (id_classe,))
        enregistrer_audit(curseur, None, "suppression_classe",
                          f"classe_id={id_classe} ref={ref}")
        conn.commit()
        return {"message": "Classe supprimée avec succès"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=409,
                            detail=f"Suppression impossible (dépendances) : {exc}")
    finally:
        curseur.close()
        conn.close()


def _creer_cycle(payload: dict):
    nom = _chaine(payload.get("nom"))
    if not nom:
        raise HTTPException(status_code=400, detail="Le nom du cycle est obligatoire")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("INSERT INTO cycle (nom) VALUES (%s)", (nom,))
        conn.commit()
        return {"message": "Cycle ajouté avec succès", "id": curseur.lastrowid}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur ajout cycle : {exc}")
    finally:
        curseur.close()
        conn.close()


def _modifier_cycle(cycle_id: int, payload: dict):
    nom = _chaine(payload.get("nom"))
    if not nom:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("SELECT id FROM cycle WHERE id = %s", (cycle_id,))
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Cycle non trouvé")
        curseur.execute("UPDATE cycle SET nom = %s WHERE id = %s", (nom, cycle_id))
        conn.commit()
        return {"message": "Cycle modifié avec succès"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification cycle : {exc}")
    finally:
        curseur.close()
        conn.close()


def _supprimer_cycle(cycle_id: int):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("UPDATE classe SET cycle_id = NULL WHERE cycle_id = %s", (cycle_id,))
        curseur.execute("DELETE FROM cycle WHERE id = %s", (cycle_id,))
        conn.commit()
        return {"message": "cycle supprimé avec succès"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"Suppression impossible : {exc}")
    finally:
        curseur.close()
        conn.close()


def _creer_matiere(payload: dict):
    nom = _chaine(payload.get("nom"))
    if not nom:
        raise HTTPException(status_code=400, detail="Le nom de la matière est obligatoire")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("INSERT INTO matiere (nom) VALUES (%s)", (nom,))
        nouvel_id = curseur.lastrowid
        conn.commit()
        return {"message": "Matière ajoutée avec succès", "id": nouvel_id,
                "matiere": {"nom": nom}}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur ajout matière : {exc}")
    finally:
        curseur.close()
        conn.close()


def _modifier_matiere(matiere_id: int, payload: dict):
    nom = _chaine(payload.get("nom"))
    if not nom:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("UPDATE matiere SET nom = %s WHERE id = %s", (nom, matiere_id))
        conn.commit()
        return {"message": "Matière modifiée avec succès",
                "matiere": {"id": matiere_id, "nom": nom}}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification matière : {exc}")
    finally:
        curseur.close()
        conn.close()


def _supprimer_matiere(matiere_id: int):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("DELETE FROM programme WHERE matiere_id = %s", (matiere_id,))
        curseur.execute(
            """DELETE FROM note WHERE matiere_id = %s""", (matiere_id,))
        curseur.execute("DELETE FROM matiere WHERE id = %s", (matiere_id,))
        conn.commit()
        return {"message": "Matière supprimée avec succès"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"Suppression impossible : {exc}")
    finally:
        curseur.close()
        conn.close()


def _associer_programme(payload: dict):
    classe_id = _id_entier(payload.get("classe_id"))
    matiere_id = _id_entier(payload.get("matiere_id"))
    enseignant_id = _id_entier(payload.get("enseignant_id"))
    coefficient = _id_entier(payload.get("coefficient")) or 1
    if classe_id is None or matiere_id is None:
        raise HTTPException(status_code=400,
                            detail="classe_id et matiere_id sont obligatoires")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute(
            """INSERT INTO programme (classe_id, matiere_id, enseignant_id, coefficient)
               VALUES (%s, %s, %s, %s)""",
            (classe_id, matiere_id, enseignant_id, coefficient))
        nouvel_id = curseur.lastrowid
        conn.commit()
        return {"message": "Programme créé avec succès", "id": nouvel_id}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur association : {exc}")
    finally:
        curseur.close()
        conn.close()


def _modifier_programme(prog_id: int, payload: dict):
    champs = {}
    for colonne in ("classe_id", "matiere_id", "enseignant_id", "coefficient"):
        if payload.get(colonne) is not None:
            valeur = _id_entier(payload.get(colonne))
            if colonne == "coefficient":
                valeur = valeur or 1
            champs[colonne] = valeur
    if not champs:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    conn = connexion()
    curseur = conn.cursor()
    try:
        affectations = ", ".join(f"{c} = %s" for c in champs)
        curseur.execute(f"UPDATE programme SET {affectations} WHERE id = %s",
                        (*champs.values(), prog_id))
        conn.commit()
        return {"message": "Programme modifié avec succès", "programme": champs}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification programme : {exc}")
    finally:
        curseur.close()
        conn.close()


def _supprimer_programme(prog_id: int):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("DELETE FROM programme WHERE id = %s", (prog_id,))
        conn.commit()
        return {"message": "Programme supprimé avec succès"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur suppression : {exc}")
    finally:
        curseur.close()
        conn.close()


# ============================================================
# HELPERS : PERSONNEL / ENSEIGNANTS
# ============================================================

def _decouper_nom_complet(payload: dict):
    nom_complet = _chaine(payload.get("nom_complet"))
    if nom_complet:
        morceaux = nom_complet.split(None, 1)
        nom = morceaux[0]
        prenom = morceaux[1] if len(morceaux) > 1 else "-"
    else:
        nom = _chaine(payload.get("nom"), "-")
        prenom = _chaine(payload.get("prenom"), "-")
    return nom, prenom


def _creer_enseignant(payload: dict):
    nom, prenom = _decouper_nom_complet(payload)
    statut = _chaine(payload.get("statut"), "actif").lower()
    if statut not in ("actif", "inactif"):
        statut = "actif"
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute(
            """INSERT INTO enseignant (nom, prenom, sexe, date_naissance, lieu_naissance,
               adresse, telephone, email, diplome, date_embauche, statut)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (nom, prenom, _sexe(payload.get("sexe")),
             _date_sql(payload.get("date_naissance")),
             _chaine(payload.get("lieu_naissance"), "-"),
             _chaine(payload.get("adresse"), "-"),
             _chaine(payload.get("telephone"), "00000000"),
             _chaine(payload.get("email")),
             _chaine(_premier(payload.get("diplome"), payload.get("fonction")), "-"),
             _date_sql(payload.get("date_embauche"), date.today().strftime("%Y-%m-%d")),
             statut))
        nouvel_id = curseur.lastrowid
        conn.commit()
        return {"message": "Enseignant ajouté avec succès", "id": nouvel_id}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur ajout enseignant : {exc}")
    finally:
        curseur.close()
        conn.close()


_COLONNES_ENSEIGNANT = (
    "nom", "prenom", "sexe", "date_naissance", "lieu_naissance", "adresse",
    "telephone", "email", "diplome", "date_embauche", "statut",
)


def _modifier_enseignant(pid: int, payload: dict):
    champs = {}
    nom, prenom = _decouper_nom_complet(payload)
    if payload.get("nom_complet") is not None:
        champs["nom"], champs["prenom"] = nom, prenom
    for colonne in _COLONNES_ENSEIGNANT:
        if colonne in champs:
            continue
        if payload.get(colonne) is not None:
            valeur = payload.get(colonne)
            if colonne == "sexe":
                valeur = _sexe(valeur)
            elif colonne in ("date_naissance", "date_embauche"):
                valeur = _date_sql(valeur)
            elif colonne == "statut":
                valeur = _chaine(valeur, "actif").lower()
                if valeur not in ("actif", "inactif"):
                    valeur = "actif"
            else:
                valeur = _chaine(valeur)
            champs[colonne] = valeur
    if not champs:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier n'a été fourni")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("SELECT id FROM enseignant WHERE id = %s", (pid,))
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Enseignant non trouvé")
        affectations = ", ".join(f"{c} = %s" for c in champs)
        curseur.execute(f"UPDATE enseignant SET {affectations} WHERE id = %s",
                        (*champs.values(), pid))
        conn.commit()
        curseur.execute("SELECT * FROM enseignant WHERE id = %s", (pid,))
        ligne = curseur.fetchone()
        colonnes_resultat = [desc[0] for desc in curseur.description] if curseur.description else []
        fiche = dict(zip(colonnes_resultat, ligne)) if ligne else None
        if fiche is None:
            raise HTTPException(status_code=404,
                                detail="Enseignant non trouvé après modification")
        return {"message": "enseignant modifié avec succès", "enseignant": fiche}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification enseignant : {exc}")
    finally:
        curseur.close()
        conn.close()


# ============================================================
# HELPERS : FINANCE
# ============================================================

def _ajouter_paiement(payload: dict):
    """Dispatch : transaction de caisse OU paiement de scolarite eleve."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Corps JSON invalide")

    # --- Forme transaction de caisse (entree / sortie) ---
    if "beneficiaire" in payload or payload.get("type") in ("entree", "sortie"):
        genre = _chaine(payload.get("type"), "entree").lower()
        if genre not in ("entree", "sortie"):
            genre = "entree"
        conn = connexion()
        curseur = conn.cursor()
        try:
            curseur.execute(
                """INSERT INTO caisse_transaction (reference, beneficiaire, motif,
                   categorie, montant, type, mode_reglement)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (_chaine(payload.get("reference")) or None,
                 _chaine(payload.get("beneficiaire"), "-"),
                 _chaine(payload.get("motif")),
                 _chaine(payload.get("categorie")),
                 float(payload.get("montant") or 0),
                 genre,
                 _chaine(payload.get("mode_reglement"))))
            nouvel_id = curseur.lastrowid
            conn.commit()
            return {"message": "Transaction enregistrée avec succès", "id": nouvel_id}
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erreur transaction : {exc}")
        finally:
            curseur.close()
            conn.close()

    # --- Forme paiement de scolarite lie a un eleve ---
    eleve_id = _id_entier(payload.get("eleve_id"))
    if eleve_id is None:
        raise HTTPException(status_code=400,
                            detail="eleve_id ou beneficiaire requis")
    conn = connexion()
    curseur = conn.cursor()
    try:
        inscription_id = _derniere_inscription(curseur, eleve_id)
        if inscription_id is None:
            annee_id = _annee_scolaire_active(curseur)
            if annee_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Aucune année scolaire active : impossible d'enregistrer le paiement")
            classe_id = _id_entier(payload.get("classe_id"))
            if classe_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="classe_id obligatoire pour créer l'inscription "
                           "d'un élève sans inscription existante")
            curseur.execute(
                "INSERT INTO inscription (eleve_id, classe_id, annee_scolaire_id)"
                " VALUES (%s, %s, %s)",
                (eleve_id, classe_id, annee_id))
            inscription_id = curseur.lastrowid
        curseur.execute(
            """INSERT INTO paiement (inscription_id, type_frais, montant, mode_paiement,
               trimestre, mois, uuid_client) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (inscription_id,
             _type_frais(payload.get("type_frais")),
             float(payload.get("montant") or 0),
             _mode_paiement(_premier(payload.get("mode_reglement"),
                                     payload.get("mode_paiement"))),
             _trimestre(payload.get("trimestre")),
             _chaine(payload.get("mois")) or None,
             _chaine(payload.get("uuid_client")) or None))
        nouvel_id = curseur.lastrowid
        enregistrer_audit(curseur, None, "paiement_eleve",
                          f"eleve_id={eleve_id} montant={payload.get('montant')} "
                          f"type={_type_frais(payload.get('type_frais'))}")
        conn.commit()
        return {"message": "Paiement enregistré avec succès", "id": nouvel_id,
                "inscription_id": inscription_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur paiement : {exc}")
    finally:
        curseur.close()
        conn.close()


def _creer_tarif(payload: dict):
    """Accepte la forme native {classe_id, frais_inscription, montant_pension}
    ET la forme bureau {classe_id, type_frais, montant, annee_scolaire}."""
    classe_id = _id_entier(payload.get("classe_id"))
    if classe_id is None:
        raise HTTPException(status_code=400, detail="classe_id obligatoire")

    frais_inscription = payload.get("frais_inscription")
    montant_pension = payload.get("montant_pension")
    if frais_inscription is None and montant_pension is None:
        montant = float(payload.get("montant") or 0)
        if _type_frais(payload.get("type_frais")) == "Inscription":
            frais_inscription, montant_pension = montant, 0.0
        else:
            frais_inscription, montant_pension = 0.0, montant
    frais_inscription = float(frais_inscription or 0)
    montant_pension = float(montant_pension or 0)

    libelle = _chaine(payload.get("annee_scolaire"))
    conn = connexion()
    curseur = conn.cursor()
    try:
        annee_id = None
        if libelle:
            curseur.execute("SELECT id FROM annee_scolaire WHERE libelle LIKE %s LIMIT 1",
                            (libelle,))
            ligne = curseur.fetchone()
            annee_id = ligne[0] if ligne else None
        if annee_id is None:
            annee_id = _annee_scolaire_active(curseur)
        if annee_id is None:
            raise HTTPException(status_code=400,
                                detail="Aucune année scolaire active n'est définie.")
        curseur.execute(
            """INSERT INTO tarif_scolarite (classe_id, annee_scolaire_id,
               frais_inscription, montant_pension) VALUES (%s, %s, %s, %s)""",
            (classe_id, annee_id, frais_inscription, montant_pension))
        nouveau_id = curseur.lastrowid
        conn.commit()
        return {"message": "Tarif de scolarité créé avec succès", "tarif_id": nouveau_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur création tarif : {exc}")
    finally:
        curseur.close()
        conn.close()


def _modifier_tarif(tarif_id: int, payload: dict):
    champs = {}
    if payload.get("frais_inscription") is not None:
        champs["frais_inscription"] = float(payload["frais_inscription"])
    if payload.get("montant_pension") is not None:
        champs["montant_pension"] = float(payload["montant_pension"])
    if payload.get("montant") is not None:
        colonne = ("frais_inscription"
                   if _type_frais(payload.get("type_frais")) == "Inscription"
                   else "montant_pension")
        champs[colonne] = float(payload["montant"])
    if payload.get("classe_id") is not None:
        champs["classe_id"] = _id_entier(payload.get("classe_id"))
    if not champs:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    conn = connexion()
    curseur = conn.cursor()
    try:
        affectations = ", ".join(f"{c} = %s" for c in champs)
        curseur.execute(f"UPDATE tarif_scolarite SET {affectations} WHERE id = %s",
                        (*champs.values(), tarif_id))
        conn.commit()
        return {"message": "Tarif de scolarité mis à jour avec succès"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification tarif : {exc}")
    finally:
        curseur.close()
        conn.close()


# ============================================================
# HELPERS : NOTES / PRESENCES
# ============================================================

def _ajouter_note(payload: dict):
    """Forme bureau {eleve_id, matiere_id, periode, devoir1, devoir2, composition}.
    Chaque composante fournie devient une ligne note (type_evaluation)."""
    eleve_id = _id_entier(payload.get("eleve_id"))
    matiere_id = _id_entier(payload.get("matiere_id"))
    if eleve_id is None or matiere_id is None:
        raise HTTPException(status_code=400, detail="eleve_id et matiere_id requis")

    composantes = [
        ("Devoir 1", payload.get("devoir1")),
        ("Devoir 2", payload.get("devoir2")),
        ("Composition", payload.get("composition")),
    ]
    composantes = [(t, v) for t, v in composantes if v is not None]
    if not composantes:
        raise HTTPException(status_code=400, detail="Aucune note fournie")

    trimestre = _trimestre(payload.get("periode"))
    jour = _date_sql(payload.get("date_evaluation"),
                     date.today().strftime("%Y-%m-%d"))

    conn = connexion()
    curseur = conn.cursor()
    try:
        inscription_id = _derniere_inscription(curseur, eleve_id)
        if inscription_id is None:
            annee_id = _annee_scolaire_active(curseur)
            if annee_id is None:
                raise HTTPException(status_code=400,
                                    detail="Aucune inscription trouvée pour cet élève "
                                           "et aucune année scolaire active")
            classe_id = _id_entier(payload.get("classe_id"))
            if classe_id is None:
                raise HTTPException(status_code=400,
                                    detail="classe_id obligatoire pour saisir des notes "
                                           "pour un élève sans inscription existante")
            curseur.execute(
                "INSERT INTO inscription (eleve_id, classe_id, annee_scolaire_id)"
                " VALUES (%s, %s, %s)", (eleve_id, classe_id, annee_id))
            inscription_id = curseur.lastrowid
        for type_evaluation, valeur in composantes:
            curseur.execute(
                """INSERT INTO note (inscription_id, matiere_id, type_evaluation, note,
                   note_sur, date_evaluation, trimestre, uuid_client)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (inscription_id, matiere_id, type_evaluation,
                 float(valeur), 20, jour, trimestre,
                 _chaine(payload.get("uuid_client")) or None))
        enregistrer_audit(curseur, None, "saisie_notes",
                          f"eleve_id={eleve_id} matiere_id={matiere_id} "
                          f"trimestre={trimestre} nb={len(composantes)}")
        conn.commit()
        return {"message": "Notes enregistrées avec succès",
                "inscription_id": inscription_id, "nb_notes": len(composantes)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement note : {exc}")
    finally:
        curseur.close()
        conn.close()


def _ajouter_presence(payload: dict):
    eleve_id = _id_entier(payload.get("eleve_id"))
    classe_id = _id_entier(payload.get("classe_id"))
    if eleve_id is None or classe_id is None:
        raise HTTPException(status_code=400, detail="eleve_id et classe_id requis")
    statut = _statut_presence(payload.get("statut"))
    motif = _chaine(payload.get("motif"))
    justifie = "Oui" if motif else _chaine(payload.get("justifie"), "Non")
    jour = _date_sql(_premier(payload.get("date"), payload.get("date_presence")))
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("SELECT id FROM eleve WHERE id = %s", (eleve_id,))
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Élève non trouvé")
        if jour:
            curseur.execute(
                """INSERT INTO presences (eleve_id, classe_id, statut, justifie, date_presence)
                   VALUES (%s, %s, %s, %s, %s)""",
                (eleve_id, classe_id, statut, justifie, jour))
        else:
            curseur.execute(
                """INSERT INTO presences (eleve_id, classe_id, statut, justifie)
                   VALUES (%s, %s, %s, %s)""",
                (eleve_id, classe_id, statut, justifie))
        nouvel_id = curseur.lastrowid
        conn.commit()
        return {"message": "Présence ajoutée avec succès", "id": nouvel_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur présence : {exc}")
    finally:
        curseur.close()
        conn.close()


# ============================================================
# HELPERS : ANNEES SCOLAIRES / COMPTES / PARAMETRES / PLANNING
# ============================================================

def _modifier_annee(annee_id: int, payload: dict):
    champs = {}
    for colonne in ("libelle", "date_debut", "date_fin"):
        if payload.get(colonne) is not None:
            valeur = payload[colonne]
            if colonne.startswith("date_"):
                valeur = _date_sql(valeur)
                if valeur is None:
                    continue
            champs[colonne] = valeur
    est_active = payload.get("est_active")
    if est_active is not None:
        champs["est_active"] = 1 if est_active and str(est_active).lower() not in ("false", "0") else 0
    if not champs:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier")
    conn = connexion()
    curseur = conn.cursor()
    try:
        if champs.get("est_active") == 1:
            curseur.execute("UPDATE annee_scolaire SET est_active = FALSE")
        affectations = ", ".join(f"{c} = %s" for c in champs)
        curseur.execute(f"UPDATE annee_scolaire SET {affectations} WHERE id = %s",
                        (*champs.values(), annee_id))
        conn.commit()
        return {"message": "Année scolaire mise à jour avec succès"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur modification année : {exc}")
    finally:
        curseur.close()
        conn.close()


def _activer_annee(annee_id: int):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("SELECT id FROM annee_scolaire WHERE id = %s", (annee_id,))
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Année scolaire non trouvée")
        curseur.execute("UPDATE annee_scolaire SET est_active = FALSE")
        curseur.execute("UPDATE annee_scolaire SET est_active = TRUE WHERE id = %s",
                        (annee_id,))
        enregistrer_audit(curseur, None, "activation_annee_scolaire",
                          f"annee_id={annee_id}")
        conn.commit()
        return {"message": "Année scolaire activée avec succès"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur activation année : {exc}")
    finally:
        curseur.close()
        conn.close()


def _supprimer_annee(annee_id: int):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("DELETE FROM inscription WHERE annee_scolaire_id = %s", (annee_id,))
        curseur.execute("DELETE FROM tarif_scolarite WHERE annee_scolaire_id = %s", (annee_id,))
        curseur.execute("DELETE FROM annee_scolaire WHERE id = %s", (annee_id,))
        conn.commit()
        return {"message": "Année scolaire supprimée avec succès"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"Suppression impossible : {exc}")
    finally:
        curseur.close()
        conn.close()


def _creer_compte(payload: dict):
    """Forme bureau {nom, email, telephone, role, actif[, password]}.
    Le hash PBKDF2 du bureau est conserve s'il est fourni (le serveur sait
    le verifier) ; sinon un jeton aleatoire inutilisable est stocke."""
    nom = _chaine(payload.get("nom"), "-")
    email = _chaine(payload.get("email"))
    identifiant = (email.split("@")[0] if "@" in email
                   else nom.lower().replace(" ", "."))
    role = _chaine(payload.get("role"), "gestionnaire").lower()
    if role not in ("admin", "directeur", "gestionnaire", "enseignant"):
        role = "gestionnaire"
    conn = connexion()
    curseur = conn.cursor()
    try:
        base = identifiant
        compteur = 1
        while True:
            curseur.execute("SELECT id FROM utilisateur WHERE identifiant = %s",
                            (identifiant,))
            if curseur.fetchone() is None:
                break
            identifiant = f"{base}{compteur}"
            compteur += 1
        hash_stocke = _chaine(payload.get("password")) or hacher(_token_aleatoire())
        curseur.execute(
            """INSERT INTO utilisateur (nom, prenom, telephone, email, identifiant,
               mot_de_passe, role, statut) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (nom, "-", _chaine(payload.get("telephone"), "00000000"),
             email, identifiant, hash_stocke, role,
             "actif" if payload.get("actif", 1) else "inactif"))
        nouvel_id = curseur.lastrowid
        enregistrer_audit(curseur, None, "creation_compte",
                          f"identifiant={identifiant} role={role}")
        conn.commit()
        return {"message": "Utilisateur créé avec succès", "id": nouvel_id,
                "identifiant": identifiant}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur création compte : {exc}")
    finally:
        curseur.close()
        conn.close()


def hacher(mot_de_passe: str) -> str:
    """Hachage bcrypt (bcrypt tronque a 72 octets)."""
    import bcrypt
    return bcrypt.hashpw(mot_de_passe.encode("utf-8")[:72],
                         bcrypt.gensalt()).decode("utf-8")


def _definir_parametre(payload: dict):
    cle = _chaine(payload.get("cle"))
    valeur = "" if payload.get("valeur") is None else str(payload.get("valeur"))
    if not cle:
        raise HTTPException(status_code=400, detail="cle obligatoire")
    conn = connexion()
    curseur = conn.cursor()
    try:
        # Modulaire MySQL (ON DUPLICATE KEY) ET SQLite (sans upsert dedie) :
        # on teste l'existence puis insert/update selon le backend.
        curseur.execute("SELECT cle FROM parametre WHERE cle = %s", (cle,))
        if curseur.fetchone() is not None:
            curseur.execute("UPDATE parametre SET valeur = %s WHERE cle = %s",
                            (valeur, cle))
        else:
            curseur.execute("INSERT INTO parametre (cle, valeur) VALUES (%s, %s)",
                            (cle, valeur))
        conn.commit()
        return {"message": "Paramètre enregistré", "cle": cle}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur paramètre : {exc}")
    finally:
        curseur.close()
        conn.close()


def _supprimer_parametre(cle: str):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("DELETE FROM parametre WHERE cle = %s", (cle,))
        conn.commit()
        return {"message": "Paramètre supprimé", "cle": cle}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur paramètre : {exc}")
    finally:
        curseur.close()
        conn.close()


def _enregistrer_planning(payload: dict):
    classe_id = _id_entier(payload.get("classe_id"))
    if classe_id is None:
        raise HTTPException(status_code=400, detail="classe_id obligatoire")
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute(
            """INSERT INTO planning (classe_id, jour, creneau, matiere, salle)
               VALUES (%s, %s, %s, %s, %s)""",
            (classe_id, _chaine(payload.get("jour"), "-"),
             _chaine(payload.get("creneau"), "-"),
             _chaine(payload.get("matiere")),
             _chaine(payload.get("salle"))))
        nouvel_id = curseur.lastrowid
        conn.commit()
        return {"message": "Créneau enregistré", "id": nouvel_id}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur planning : {exc}")
    finally:
        curseur.close()
        conn.close()


def _vider_planning(classe_id: int):
    conn = connexion()
    curseur = conn.cursor()
    try:
        curseur.execute("DELETE FROM planning WHERE classe_id = %s", (classe_id,))
        conn.commit()
        return {"message": "Planning vidé", "classe_id": classe_id}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur planning : {exc}")
    finally:
        curseur.close()
        conn.close()


# ============================================================
# ENREGISTREMENT DES ROUTES DE COMPATIBILITE
# ============================================================

def enregistrer_routes_compat(app):
    """Appele depuis main.py juste apres la creation de l'app FastAPI :
    les routes ci-dessous sont donc examinees AVANT les routes historiques."""

    # ---------- Eleves ----------
    @app.post("/eleve")
    def _compat_post_eleve(payload: dict = Body(...)):
        return _creer_eleve_complet(payload)

    @app.put("/modifierEleve/{eleve_id}")
    def _compat_put_eleve(eleve_id: int, payload: dict = Body(...)):
        return _modifier_eleve(eleve_id, payload)

    @app.delete("/eleve/{eleve_id}/notes")
    def _compat_del_notes(eleve_id: int):
        return _vider_donnees_eleve(eleve_id, "note")

    @app.delete("/eleve/{eleve_id}/presences")
    def _compat_del_presences(eleve_id: int):
        return _vider_donnees_eleve(eleve_id, "presences")

    @app.delete("/eleve/{eleve_id}/paiements")
    def _compat_del_paiements(eleve_id: int):
        return _vider_donnees_eleve(eleve_id, "paiement")

    # ---------- Classes / Cycles ----------
    @app.post("/classe")
    def _compat_post_classe(payload: dict = Body(...)):
        return _creer_classe(payload)

    @app.put("/modifierClasse/{classe_id}")
    def _compat_put_classe(classe_id: int, payload: dict = Body(...)):
        return _modifier_classe(classe_id, payload)

    @app.delete("/supprimerClasse/{ref}")
    def _compat_del_classe(ref: str):
        return _supprimer_classe(ref)

    @app.post("/cycle")
    def _compat_post_cycle(payload: dict = Body(...)):
        return _creer_cycle(payload)

    @app.put("/modifierCycle/{cycle_id}")
    def _compat_put_cycle(cycle_id: int, payload: dict = Body(...)):
        return _modifier_cycle(cycle_id, payload)

    @app.delete("/supprimerCycle/{cycle_id}")
    def _compat_del_cycle(cycle_id: int):
        return _supprimer_cycle(cycle_id)

    # ---------- Matieres / Programmes ----------
    @app.post("/matiere")
    def _compat_post_matiere(payload: dict = Body(...)):
        return _creer_matiere(payload)

    @app.put("/modifierMatiere/{matiere_id}")
    def _compat_put_matiere(matiere_id: int, payload: dict = Body(...)):
        return _modifier_matiere(matiere_id, payload)

    @app.delete("/supprimerMatiere/{matiere_id}")
    def _compat_del_matiere(matiere_id: int):
        return _supprimer_matiere(matiere_id)

    @app.post("/associerMatiereClasseEnseignant")
    def _compat_post_programme(payload: dict = Body(...)):
        return _associer_programme(payload)

    @app.put("/modifierProgramme/{prog_id}")
    def _compat_put_programme(prog_id: int, payload: dict = Body(...)):
        return _modifier_programme(prog_id, payload)

    @app.delete("/supprimerProgramme/{prog_id}")
    def _compat_del_programme(prog_id: int):
        return _supprimer_programme(prog_id)

    # ---------- Enseignants / Personnel ----------
    @app.post("/enseignant")
    def _compat_post_enseignant(payload: dict = Body(...)):
        return _creer_enseignant(payload)

    @app.get("/enseignant/{enseignant_id}")
    def _compat_get_enseignant(enseignant_id: int):
        conn = connexion()
        curseur = conn.cursor(dictionary=True)
        try:
            curseur.execute("SELECT * FROM enseignant WHERE id = %s", (enseignant_id,))
            ligne = curseur.fetchone()
            return {"enseignant": ligne}
        finally:
            curseur.close()
            conn.close()

    @app.put("/modifierEnseignant/{enseignant_id}")
    def _compat_put_enseignant(enseignant_id: int, payload: dict = Body(...)):
        return _modifier_enseignant(enseignant_id, payload)

    @app.delete("/supprimerEnseignant/{enseignant_id}")
    def _compat_del_enseignant(enseignant_id: int):
        conn = connexion()
        curseur = conn.cursor()
        try:
            curseur.execute("DELETE FROM enseignant WHERE id = %s", (enseignant_id,))
            if curseur.rowcount == 0:
                raise HTTPException(status_code=404, detail="enseignant non trouvé")
            conn.commit()
            return {"message": "enseignant supprimé avec succès"}
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            curseur.close()
            conn.close()

    # ---------- Finance ----------
    @app.post("/paiement")
    def _compat_post_paiement(payload: dict = Body(...)):
        return _ajouter_paiement(payload)

    @app.post("/tarifs-scolarite")
    def _compat_post_tarif(payload: dict = Body(...)):
        return _creer_tarif(payload)

    @app.put("/tarifs-scolarite/{tarif_id}")
    def _compat_put_tarif(tarif_id: int, payload: dict = Body(...)):
        return _modifier_tarif(tarif_id, payload)

    @app.get("/tarifs-scolarite")
    def _compat_get_tarifs():
        conn = connexion()
        curseur = conn.cursor(dictionary=True)
        try:
            curseur.execute(
                """SELECT t.id AS tarif_id, t.classe_id, t.annee_scolaire_id,
                          c.classe AS classe_nom, a.libelle AS annee_scolaire,
                          t.frais_inscription, t.montant_pension
                   FROM tarif_scolarite t
                   LEFT JOIN classe c ON c.id = t.classe_id
                   LEFT JOIN annee_scolaire a ON a.id = t.annee_scolaire_id
                   ORDER BY c.classe""")
            lignes = curseur.fetchall()
            return {"tarifs": lignes}
        finally:
            curseur.close()
            conn.close()

    @app.get("/tarifs-scolarite/classe/{classe_id}")
    def _compat_get_tarifs_classe(classe_id: int):
        conn = connexion()
        curseur = conn.cursor(dictionary=True)
        try:
            curseur.execute(
                """SELECT t.id AS tarif_id, t.classe_id, t.annee_scolaire_id,
                          c.classe AS classe_nom, a.libelle AS annee_scolaire,
                          t.frais_inscription, t.montant_pension
                   FROM tarif_scolarite t
                   LEFT JOIN classe c ON c.id = t.classe_id
                   LEFT JOIN annee_scolaire a ON a.id = t.annee_scolaire_id
                   WHERE t.classe_id = %s ORDER BY a.libelle DESC""", (classe_id,))
            lignes = curseur.fetchall()
            return {"tarifs": lignes}
        finally:
            curseur.close()
            conn.close()

    @app.get("/paiement/bilan/type_frais/{type_frais}")
    def _compat_bilan_type_frais(type_frais: str):
        conn = connexion()
        curseur = conn.cursor(dictionary=True)
        try:
            curseur.execute(
                "SELECT type_frais, SUM(montant) AS total_montant FROM paiement"
                " WHERE LOWER(type_frais) = LOWER(%s) GROUP BY type_frais", (type_frais,))
            return {"paiement": curseur.fetchall()}
        finally:
            curseur.close()
            conn.close()

    # ---------- Notes / Presences ----------
    @app.post("/note")
    def _compat_post_note(payload: dict = Body(...)):
        return _ajouter_note(payload)

    @app.post("/presence")
    def _compat_post_presence(payload: dict = Body(...)):
        return _ajouter_presence(payload)

    # ---------- Annees scolaires ----------
    @app.put("/annee_scolaire/{annee_id}")
    def _compat_put_annee(annee_id: int, payload: dict = Body(...)):
        return _modifier_annee(annee_id, payload)

    @app.put("/annee_scolaire/{annee_id}/actif")
    def _compat_activer_annee(annee_id: int):
        return _activer_annee(annee_id)

    @app.delete("/annee_scolaire/{annee_id}")
    def _compat_del_annee(annee_id: int):
        return _supprimer_annee(annee_id)

    # ---------- Comptes / Parametres / Planning / Divers ----------
    @app.post("/comptes")
    def _compat_post_compte(payload: dict = Body(...)):
        return _creer_compte(payload)

    @app.post("/parametre")
    def _compat_post_parametre(payload: dict = Body(...)):
        return _definir_parametre(payload)

    @app.delete("/parametre/{cle}")
    def _compat_del_parametre(cle: str):
        return _supprimer_parametre(cle)

    @app.post("/planning")
    def _compat_post_planning(payload: dict = Body(...)):
        return _enregistrer_planning(payload)

    @app.delete("/planning/{classe_id}")
    def _compat_del_planning(classe_id: int):
        return _vider_planning(classe_id)

    @app.get("/total_classe")
    def _compat_total_classe():
        conn = connexion()
        curseur = conn.cursor()
        try:
            curseur.execute("SELECT COUNT(*) FROM classe")
            return {"total_classe": curseur.fetchone()[0]}
        finally:
            curseur.close()
            conn.close()

    # ---------- Piste d'audit (lecture reservee admin/directeur) ----------
    @app.get("/audit")
    def _compat_consulter_audit(limite: int = 200,
                                authorization: str = Header(None)):
        identite = _identite_depuis_token(authorization)
        if str(identite.get("role", "")).lower() not in ("admin", "administrateur",
                                                         "directeur"):
            raise HTTPException(status_code=403,
                                detail="Consultation de l'audit reservee "
                                       "aux administrateurs et directeurs.")
        conn = connexion()
        curseur = conn.cursor()
        try:
            curseur.execute(
                "SELECT id, horodatage, utilisateur_id, action, details, adresse_ip"
                " FROM audit_log ORDER BY id DESC LIMIT %s",
                (max(1, min(int(limite), 1000)),))
            colonnes = ["id", "horodatage", "utilisateur_id", "action",
                        "details", "adresse_ip"]
            return [dict(zip(colonnes, ligne)) for ligne in curseur.fetchall()]
        finally:
            curseur.close()
            conn.close()

    return app
