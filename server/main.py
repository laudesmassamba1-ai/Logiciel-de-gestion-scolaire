from fastapi import FastAPI, Path, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import date
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
import mysql.connector
import os
import sys
import time
import jwt
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Charge le fichier .env AVANT toute lecture des variables d'environnement
import securite


def _dossier_serveur() -> str:
    """Dossier des donnees du serveur (schema.sql, .env).

    Mode source : a cote de ce module. Exe PyInstaller : sous sys._MEIPASS
    (les schemas sont embarques en datas dans le dossier "server").
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "server")
    return os.path.dirname(os.path.abspath(__file__))

DB_HOST = os.environ.get("GS_DB_HOST", "localhost")
DB_USER = os.environ.get("GS_DB_USER", "root")
# Aucun mot de passe par defaut : definir GS_DB_PASSWORD dans .env ou l'environnement
DB_PASSWORD = os.environ.get("GS_DB_PASSWORD", "")
DB_NAME = os.environ.get("GS_DB_NAME", "ecole")
DB_PORT = int(os.environ.get("GS_DB_PORT", "3306"))

@asynccontextmanager
async def _startup_shutdown(app: FastAPI):
    """Remplace @app.on_event("startup") deprecie par le gestionnaire de
    cycle de vie (FastAPI >= 0.97). Initialise la base MySQL ou SQLite."""
    if os.environ.get("GS_DB_MODE", "").strip().lower() == "sqlite":
        print(" Mode SQLite : base fichier, schema auto-applique.")
        yield
        return
    conn = mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")
    chemin_schema = os.path.join(_dossier_serveur(), "schema.sql")
    with open(chemin_schema, "r", encoding="utf-8") as f:
        script_sql = f.read()
    instructions = [req.strip() for req in script_sql.split(";") if req.strip()]
    for instruction in instructions:
        lignes_utiles = [
            l for l in instruction.split("\n") if l.strip() and not l.strip().startswith("--")
        ]
        if not lignes_utiles:
            continue
        instruction_propre = "\n".join(lignes_utiles)
        try:
            cursor.execute(instruction_propre)
        except mysql.connector.Error as err:
            if err.errno != 1050:
                raise
    compat.creer_tables_complementaires(cursor)
    conn.commit()
    cursor.close()
    conn.close()
    print(" Base de données vérifiée/créée avec succès au démarrage.")
    yield


app = FastAPI(lifespan=_startup_shutdown)

_origins_brut = os.environ.get("GS_CORS_ORIGINS", "*")
ORIGINS_AUTORISEES = [o.strip() for o in _origins_brut.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    # Un joker "*" est incompatible avec allow_credentials (spec Fetch) :
    # on n'active les credentials que pour une liste explicite d'origines.
    allow_origins=ORIGINS_AUTORISEES,
    allow_credentials="*" not in ORIGINS_AUTORISEES,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _cloisonner_ecoles(request: Request, call_next):
    """Refuse les appels venant d'un poste d'un AUTRE etablissement.

    Quand GS_ECOLE_CODE est configure, chaque requete doit porter
    l'en-tete X-Ecole-Code avec le meme code (mis par api/client.py).
    Sans cela, une ecole pourrait se synchroniser avec le serveur d'une
    autre ecole voisine : c'est le verrou de difference entre ecoles.
    """
    from fastapi.responses import JSONResponse
    if securite.ECOLE_CODE and request.url.path not in (
            "/ecole", "/docs", "/openapi.json", "/redoc"):
        code_entete = request.headers.get("x-ecole-code", "")
        if not securite.ecole_autorisee(code_entete):
            return JSONResponse(
                status_code=403,
                content={"detail": "Code de l'ecole invalide : ce serveur "
                         "appartient a un autre etablissement."})
    return await call_next(request)


@app.get("/ecole")
def identite_ecole():
    """Code de l'etablissement heberge par ce serveur.

    Accessible SANS code : c'est l'information qu'un poste lit pour se
    rapprocher (et verifier) sa propre ecole. La confidentialite des
    donnees reste protegee par le cloisonnement de toutes les autres routes.
    """
    return {"code_ecole": securite.ECOLE_CODE}

# Routes de compatibilite avec l'application de bureau (enregistrees en premier)
import compat
compat.enregistrer_routes_compat(app)

def get_connection():
    # Mode "sans installation" : tout passe par le backend SQLite.
    if os.environ.get("GS_DB_MODE", "").strip().lower() == "sqlite":
        try:
            from server.sqlite_backend import connexion_sqlite
        except ImportError:
            from sqlite_backend import connexion_sqlite
        return connexion_sqlite()
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    # On convertit en bytes et on tronque à 72 octets max pour éviter tout blocage
    pwd_bytes = mot_de_passe.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe_brut: str, hash_stocke: str) -> bool:
    # Compatibilite desktop : les comptes crees hors serveur utilisent
    # PBKDF2-HMAC-SHA256 au format "salt_hex:hash_hex" (cf. database/db.py).
    # Un hash bcrypt ne contient jamais de ":".
    if ":" in hash_stocke:
        try:
            import hashlib
            import hmac as _hmac
            salt_hex, h_hex = hash_stocke.split(":", 1)
            calcule = hashlib.pbkdf2_hmac(
                "sha256", mot_de_passe_brut.encode("utf-8"),
                bytes.fromhex(salt_hex), 100000).hex()
            return _hmac.compare_digest(calcule, h_hex)
        except ValueError:
            return False
    pwd_bytes = mot_de_passe_brut.encode("utf-8")[:72]
    hash_bytes = hash_stocke.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


def _redoublant_sql(valeur) -> str:
    """Coin retenu par l'ENUM MySQL eleve.redoublant : '0'/'1'.
    Le bureau peut envoyer 0/1 (int) ou "0"/"1" (str)."""
    s = str(valeur or 0)
    return s if s in ("0", "1") else "0"


def _oui_non_sql(valeur) -> str:
    """Normalise un booleen/texte vers la valeur ENUM MySQL ('Oui'/'Non')."""
    s = str(valeur or "").strip().lower()
    return "Oui" if s in ("1", "oui", "true", "vrai", "yes", "present") else "Non"


#affichage du nombre total d'élèves
@app.get("/total_eleves")
def get_total_eleves()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM eleve WHERE est_supprime = 0")
        total_eleves = cursor.fetchone()[0]
        return {"total_eleves": total_eleves}
    finally:
        cursor.close()
        conn.close()

# afficher le nombre total d'eleves par sexe 
@app.get("/total_eleve_par_sexe")
def get_total_eleve_par_sexe() -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # Retourne les résultats sous forme de dictionnaires
    try:
        # On sélectionne aussi la colonne 'sexe'
        cursor.execute("SELECT sexe, COUNT(*) AS total FROM eleve WHERE est_supprime = 0 GROUP BY sexe")
        total_eleve_par_sexe = cursor.fetchall()
        
        # Format propre retourné : {"total_eleves_par_sexe": [{"sexe": "M", "total": 150}, {"sexe": "F", "total": 120}]}
        return {"total_eleves_par_sexe": total_eleve_par_sexe}
    finally:
        cursor.close()
        conn.close()

#affichage du nombre total d'élèves par classe
@app.get("/total_eleves_par_classe")
def get_total_eleves_par_classe(recherche: Optional[str] = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not recherche:
            return {
                "message": (
                    "Veuillez fournir un nom de classe dans le paramètre"
                    " 'recherche'."
                )
            }

        motif = f"%{recherche}%"

        # 1. Compter les élèves (Utilisation de LIKE au lieu de =)
        sql_count = """
            SELECT COUNT(*) 
            FROM eleve 
            INNER JOIN inscription ON inscription.eleve_id = eleve.id 
            INNER JOIN classe ON inscription.classe_id = classe.id 
            WHERE classe.classe LIKE %s AND eleve.est_supprime = 0
        """
        cursor.execute(sql_count, (motif,))
        total_eleves = cursor.fetchone()[0]

        # 2. Récupérer le vrai nom de la classe
        cursor.execute(
            "SELECT classe FROM classe WHERE classe LIKE %s LIMIT 1", (motif,)
        )
        res_classe = cursor.fetchone()

        nom_classe = res_classe[0] if res_classe else recherche

        # Cle canonique + ancienne cle conservee pour compatibilite.
        return {"total_eleves_par_classe": {nom_classe: total_eleves},
                "nombre total d'élèves": {nom_classe: total_eleves}}

    finally:
        cursor.close()
        conn.close()

# afficher le nombre total d'eleves par classe
@app.get("/total_eleve_par_classe")
def get_total_eleve_par_classe() -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # On suppose que la colonne s'appelle 'classe' dans la table 'eleve'
        cursor.execute("SELECT classe, COUNT(*) AS total FROM eleve, classe, inscription where eleve.id=inscription.eleve_id and inscription.classe_id=classe.id and eleve.est_supprime = 0 GROUP BY classe")
        total_eleve_par_classe = cursor.fetchall()
        
        return {"total_eleves_par_classe": total_eleve_par_classe}
    finally:
        cursor.close()
        conn.close()

# afficher le nombre de garcons et de filles pour une classe donnee
@app.get("/total_eleve_par_sexe_par_classe")
def get_total_eleve_par_sexe_par_classe(classe: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT sexe, COUNT(*) AS total FROM eleve, classe, inscription WHERE eleve.id=inscription.eleve_id and inscription.classe_id=classe.id and eleve.est_supprime = 0 and classe = %s GROUP BY sexe",
            (classe,)
        )
        resultats = cursor.fetchall()
        
        return {
            "classe": classe,
            "statistiques": resultats
        }
    finally:
        cursor.close()
        conn.close()

#affichage de la liste des élèves par classe
@app.get("/eleve/{classe}")
def get_all_eleves_par_classe(classe: str)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Le client peut transmettre un id numerique OU le libelle de classe.
    base_sql = ("SELECT eleve.id, nom, prenom, sexe FROM eleve, inscription, classe "
                "where inscription.classe_id=classe.id and "
                "inscription.eleve_id=eleve.id and eleve.est_supprime = 0")
    try:
        filtre_id = int(classe)
    except ValueError:
        filtre_id = None
    if filtre_id is not None:
        cursor.execute(base_sql + " and classe.id = %s", (filtre_id,))
    else:
        cursor.execute(base_sql + " and classe.classe = %s", (classe,))
    eleves = cursor.fetchall()
    return {"eleves": eleves}

#affchage de la liste de tous les eleves
@app.get("/eleve")
def get_all_eleves()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT eleve.*, classe FROM eleve, inscription, classe where inscription.classe_id=classe.id and inscription.eleve_id=eleve.id and eleve.est_supprime = 0")
    eleves = cursor.fetchall()
    return {"eleves": eleves}

#affichage d'un élève par son nom
@app.get("/eleve_recherche")
def get_eleve_par_son_nom(recherche: Optional[str]=None, recherche1: Optional[str]=None)-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # WHERE dynamique : chaque parametre fourni filtre, les autres sont
    # ignores (avant : prenom like None renvoyait des resultats faux).
    conditions, params = [], []
    if recherche:
        conditions.append("eleve.nom LIKE %s")
        params.append(f"%{recherche}%")
    if recherche1:
        conditions.append("eleve.prenom LIKE %s")
        params.append(f"%{recherche1}%")
    sql = """select eleve.id, nom, prenom, sexe, classe.classe AS classe,
             date_naissance, lieu_naissance, eleve.adresse AS adresse,
             eleve.nom_parent AS nom_parent, redoublant, eleve.statut AS statut,
             numero_parent
             from eleve, inscription, classe
             where inscription.eleve_id=eleve.id and inscription.classe_id=classe.id"""
    if conditions:
        sql += " and " + " and ".join(conditions)
    cursor.execute(sql, tuple(params))

    eleve = cursor.fetchall()

    if eleve is None:
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    cursor.close()
    conn.close()
    return {"eleve": eleve}

#affichage du nombre total d'eleve par classe
@app.get("/eleve_total_classe")
def get_eleve_total_classe():
    conn= get_connection()
    cursor= conn.cursor(dictionary=True)
    cursor.execute("select count(*) as 'nombre_eleve', classe from eleve, classe, inscription where inscription.classe_id=classe.id and inscription.eleve_id=eleve.id and est_supprime=0 group by classe.classe ")
    eleve_total_classe=cursor.fetchall()
    cursor.close()
    conn.close()
    return {"eleve_total_classe": eleve_total_classe}

# 1. Modèles Pydantic
class Eleveajouter(BaseModel):
    nom: str
    prenom: str
    sexe: str
    date_naissance: str
    lieu_naissance: str
    adresse: str
    nom_parent: str
    redoublant: Optional[str]   # "0" pour Non, "1" pour Oui
    statut: str
    classe_id: int  # Transmis par le front pour l'inscription !
    telephone_parent: str
    uuid_client: Optional[str] = None


class paiementAjouter(BaseModel):
    type_frais: str
    montant: float
    mode_paiement: str
    trimestre: Optional[str] = None
    mois: Optional[str] = None
    uuid_client: Optional[str] = None


class RequeteAjoutEleve(BaseModel):
    eleve: Eleveajouter
    paiement: paiementAjouter
    uuid_client: Optional[str] = None


# 2. Route POST
@app.post("/ajout_eleve")
def ajouter_eleve(payload: RequeteAjoutEleve):
    eleve = payload.eleve
    paiement = payload.paiement
    # On récupère l'UUID du payload global ou de l'élève
    uuid_client = payload.uuid_client or eleve.uuid_client

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # A. Vérification anti-doublon pour le mode hors-ligne
        if uuid_client:
            cursor.execute(
                "SELECT id FROM eleve WHERE uuid_client = %s", (uuid_client,)
            )
            existant = cursor.fetchone()
            if existant:
                return {
                    "message": "Élève déjà enregistré (synchronisé)",
                    "eleve_id": existant["id"],
                }

        # B. Insertion de l'élève (SANS classe_id dans la table eleve)
        sql_eleve = """
            INSERT INTO eleve (
                nom, prenom, sexe, date_naissance,
                lieu_naissance, adresse, nom_parent,
                redoublant, statut, numero_parent, uuid_client
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valeurs_eleve = (
            eleve.nom,
            eleve.prenom,
            compat._sexe(eleve.sexe),
            eleve.date_naissance,
            eleve.lieu_naissance,
            eleve.adresse,
            eleve.nom_parent,
            _redoublant_sql(eleve.redoublant),
            compat._statut_eleve(eleve.statut),
            eleve.telephone_parent,
            uuid_client,
        )
        cursor.execute(sql_eleve, valeurs_eleve)
        eleve_id = cursor.lastrowid

        # C. Récupération de l'année scolaire active
        cursor.execute(
            "SELECT id FROM annee_scolaire WHERE est_active = TRUE LIMIT 1"
        )
        annee_active = cursor.fetchone()

        if not annee_active:
            raise HTTPException(status_code=400, detail="Aucune année scolaire active n'a été trouvée.")

        annee_scolaire_id = annee_active["id"]

        # D. Insertion dans la table inscription (Utilise eleve.classe_id)
        sql_inscription = """
            INSERT INTO inscription (eleve_id, classe_id, annee_scolaire_id) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(
            sql_inscription, (eleve_id, eleve.classe_id, annee_scolaire_id)
        )
        inscription_id = cursor.lastrowid

        # E. Insertion du paiement lié à l'inscription
        sql_paiement = """
            INSERT INTO paiement (
                inscription_id, type_frais, montant, mode_paiement, trimestre, mois, uuid_client
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        valeurs_paiement = (
            inscription_id,
            compat._type_frais(paiement.type_frais),
            paiement.montant,
            compat._mode_paiement(paiement.mode_paiement),
            compat._trimestre(paiement.trimestre),
            paiement.mois,
            paiement.uuid_client,
        )
        cursor.execute(sql_paiement, valeurs_paiement)

        # F. Validation globale de la transaction
        conn.commit()

        return {
            "message": (
                "Élève, inscription et paiement enregistrés avec succès !"
            ),
            "eleve_id": eleve_id,
            "inscription_id": inscription_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'enregistrement : {str(e)}",
        )

    finally:
        cursor.close()
        conn.close()

class EleveModifier(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    date_naissance: Optional[str] = None
    lieu_naissance: Optional[str] = None
    adresse: Optional[str] = None
    nom_parent: Optional[str] = None
    redoublant: Optional[str] = None
    statut: Optional[str] = None
    numero_parent: Optional[str] = None
    classe_id: Optional[int] = None  # Permet de modifier la classe si fourni !


@app.put("/eleve/{eleve_id}")
def modifier_eleve(eleve_id: int, eleve: EleveModifier):
    nouvelles_donnees = eleve.model_dump(exclude_unset=True)

    if not nouvelles_donnees:
        raise HTTPException(
            status_code=400, detail="Aucun champ à modifier n'a été fourni"
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Vérifier si l'élève existe
        cursor.execute("SELECT id FROM eleve WHERE id=%s", (eleve_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Élève non trouvé")

        # 2. Extraire classe_id s'il est présent (géré séparément dans 'inscription')
        nouvelle_classe_id = nouvelles_donnees.pop("classe_id", None)

        # Normalisation des valeurs d'ENUM MySQL (le bureau envoie le
        # vocabulaire métier : « Inscrit », « Exclu », redoublant 0/1).
        if "statut" in nouvelles_donnees:
            nouvelles_donnees["statut"] = compat._statut_eleve(
                nouvelles_donnees["statut"])
        if "redoublant" in nouvelles_donnees:
            nouvelles_donnees["redoublant"] = _redoublant_sql(
                nouvelles_donnees["redoublant"])

        # 3. Mise à jour dynamique de la table 'eleve'
        if nouvelles_donnees:
            nouvelles_donnees = {k: v for k, v in nouvelles_donnees.items() if v is not None}
        if nouvelles_donnees:
            clauses_set = [f"{cle}=%s" for cle in nouvelles_donnees.keys()]
            sql = f"UPDATE eleve SET {', '.join(clauses_set)} WHERE id=%s"

            valeurs = list(nouvelles_donnees.values())
            valeurs.append(eleve_id)
            cursor.execute(sql, tuple(valeurs))

        # 4. Si classe_id est fourni, mettre à jour dans la table 'inscription'
        if nouvelle_classe_id is not None:
            cursor.execute(
                "SELECT id FROM annee_scolaire WHERE est_active = TRUE LIMIT 1"
            )
            annee_active = cursor.fetchone()
            if annee_active:
                cursor.execute(
                    """
                    UPDATE inscription 
                    SET classe_id = %s 
                    WHERE eleve_id = %s AND annee_scolaire_id = %s
                """,
                    (nouvelle_classe_id, eleve_id, annee_active["id"]),
                )

        conn.commit()

        # 5. Récupérer la fiche complète à jour
        cursor.execute("SELECT * FROM eleve WHERE id=%s", (eleve_id,))
        eleve_mis_a_jour = cursor.fetchone()

        return {
            "message": "Élève modifié avec succès",
            "eleve": eleve_mis_a_jour,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la modification : {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()

#route pour supprimer un élève
@app.delete("/eleve/{id}")
def supprimer_eleve(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    # On marque l'élève comme archivé/supprimé
    cursor.execute("UPDATE eleve SET est_supprime = TRUE WHERE id = %s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "Élève archivé avec succès"}

#route pour afficher les eleves supprimés/archivés
@app.get("/eleve_supprime")
def get_eleves_supprimes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nom, prenom, sexe, classe.classe, date_naissance, lieu_naissance, adresse, nom_parent, redoublant, numero_parent FROM eleve, classe, inscription  WHERE inscription.classe_id=classe.id and inscription.eleve_id=eleve.id and est_supprime = TRUE")
    eleves_supprimes = cursor.fetchall()
    return {"eleves_supprimes": eleves_supprimes}

#route pour restaurer un élève supprimé/archivé
@app.put("/restaurer_eleve/{nom}/{prenom}")
def restaurer_eleve(nom: str, prenom: str):
    conn = get_connection()
    cursor = conn.cursor()

    # On restaure l'élève en le démarquant comme non-supprimé.
    # Sous-requête : si plusieurs élèves partagent le même
    # nom/prenom, seul le plus récent (est_supprime=TRUE) est restauré.
    # Table derivee (double SELECT) : MySQL interdit de mettre a jour la
    # table cible selectionnee dans la sous-requete de la meme instruction
    # (erreur 1093) ; cette forme est valide en MySQL ET en SQLite.
    cursor.execute(
        "UPDATE eleve SET est_supprime = FALSE "
        "WHERE id = (SELECT id FROM (SELECT id FROM eleve WHERE nom = %s AND prenom = %s "
        "AND est_supprime = TRUE ORDER BY id DESC LIMIT 1) AS tmp)",
        (nom, prenom))
    conn.commit()
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Élève archivé non trouvé")
    cursor.close()
    conn.close()

    return {"message": "Élève restauré avec succès"}

#route pour afficher la liste des parents par classe
@app.get("/parents_par_classe/{classe_name}")
def get_parents_par_classe(classe_name: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT nom, prenom, nom_parent, numero_parent, classe FROM eleve, classe, inscription 
        WHERE inscription.classe_id = classe.id and inscription.eleve_id=eleve.id AND classe.classe LIKE %s
    """, (f"{classe_name}",))
    parents = cursor.fetchall()
    return {"parents": parents}

#route pour afficher le total des classes
@app.get("/total_classe")
def get_total_classe()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM classe")
    total_classe = cursor.fetchone()[0]
    return {"total_classe": total_classe}

#affichage de la liste des classes
@app.get("/classe")
def get_all_classe()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # On sélectionne directement les bonnes colonnes avec les bons alias :
    # le client de synchro lit "nom" comme libelle de classe et "id" pour
    # rattacher ses eleves (correction reprise depuis gestion_scolaire_api).
    cursor.execute("SELECT id, classe AS nom, cycle_id FROM classe")
    classes = cursor.fetchall()
    return {"classes": classes}

#affichage d'une classe par son nom
@app.get("/classe/{classe}")
def get_classe_par_id(classe: str)-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM classe WHERE classe = %s", (classe,))
    classe = cursor.fetchone()
    if classe is None:
        raise HTTPException(status_code=404, detail="classe non trouvée")
    return {"classe": classe}

# Modèle des données attendues dans le corps de la requête (JSON)
class classeAjouter(BaseModel):
    classe: str
    cycle_id: int
    uuid_client: Optional[str] = None

# 2. Route POST pour ajouter une classe
@app.post("/ajout_classe")
def ajouter_classe(classe: classeAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO classe (
           classe, cycle_id
        ) VALUES (%s, %s)
    """

    valeurs = (
       classe.classe,
       classe.cycle_id
    )

    try:
        cursor.execute(sql, valeurs)
        conn.commit()
        nouvel_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return {
        "message": "classe ajoutée avec succès",
        "id": nouvel_id,
        "classe": classe.model_dump()
    }

class ClasseModifier(BaseModel):
    classe: Optional[str] = None
    cycle_id: Optional[int] = None

#route pour modifier une classe
@app.put("/classe/{classe_id}")
def put_une_classe(classe_id: int, classe_data: ClasseModifier):
    # Récupère UNIQUEMENT les champs envoyés dans Swagger/Postman
    nouvelles_donnees = classe_data.model_dump(exclude_unset=True)

    if not nouvelles_donnees:
        raise HTTPException(
            status_code=400, detail="Aucun champ à modifier n'a été fourni."
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Vérifier si la classe existe
        cursor.execute("SELECT id FROM classe WHERE id = %s", (classe_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Classe introuvable.")

        # 2. Construction dynamique de la requête UPDATE
        clauses_set = [f"{cle} = %s" for cle in nouvelles_donnees.keys()]
        sql = f"UPDATE classe SET {', '.join(clauses_set)} WHERE id = %s"

        valeurs = list(nouvelles_donnees.values())
        valeurs.append(classe_id)

        cursor.execute(sql, tuple(valeurs))
        conn.commit()

        return {
            "message": "Classe mise à jour avec succès !",
            "champs_modifies": nouvelles_donnees,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la modification : {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()

#route pour supprimer une classe
@app.delete("/supprimerClasse/{classe}")
def delete_un_classe(classe: str):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)

    try:
        # 1. Récupérer l'élève / vérifier existence
        cursor.execute("SELECT id FROM classe WHERE classe = %s", (classe,))
        resultat = cursor.fetchone()

        # Si fetchone() vaut None, on gère l'erreur 404 tout de suite
        if resultat is None:
            raise HTTPException(status_code=404, detail="Classe non trouvée")

        id_classe = resultat[0]

        # 2. Supprimer par ID
        cursor.execute("DELETE FROM classe WHERE id = %s", (id_classe,))
        conn.commit()

        return {"message": "Classe supprimée avec succès"}

    finally:
        cursor.close()
        conn.close()

#route pour afficher le total des cycles
@app.get("/total_cycle")
def get_total_cycle()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cycle")
    total_cycle = cursor.fetchone()[0]
    return {"total_cycle": total_cycle}

#affichage de la liste des cycles
@app.get("/cycle")
def get_all_cycle()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cycle")
    cycle = cursor.fetchall()
    return {"cycle": cycle}

#affichage d'un cycle par son id
@app.get("/cycle/{id}")
def get_cycle_par_id(id: int = Path(ge=1))-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cycle WHERE id = %s", (id,))
    cycle = cursor.fetchone()
    if cycle is None:
        raise HTTPException(status_code=404, detail="cycle non trouvé")
    return {"cycle": cycle}

# Modèle des données attendues dans le corps de la requête (JSON)
class cycleAjouter(BaseModel):
    nom: str   

# 2. Route POST pour ajouter l'élève
@app.post("/ajout_cycle")
def ajouter_cycle(cycle: cycleAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO cycle (
           nom
        ) VALUES (%s)
    """

    valeurs = (
      cycle.nom,
    )

    try:
        cursor.execute(sql, valeurs)
        conn.commit()
        nouvel_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return {
        "message": "cycle ajouté avec succès",
        "id": nouvel_id,
        "cycle": cycle.model_dump()
    }


class CycleModifier(BaseModel):
    nom: Optional[str] = None

#route pour modifier un cycle
@app.put("/modifierCycle/{cycle_id}")
def put_un_cycle(cycle_id: int, cycle: CycleModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Vérifier si le cycle existe
        cursor.execute("SELECT id FROM cycle WHERE id = %s", (cycle_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle non trouvé")

        # 2. Mise à jour
        if cycle.nom:
            cursor.execute(
                "UPDATE cycle SET nom = %s WHERE id = %s", (cycle.nom, cycle_id)
            )
            conn.commit()

        # 3. Renvoyer la donnée avec la variable 'cycle_id' (sans guillemets)
        return {
            "message": "cycle modifié avec succès",
            "cycle": {
                "id": cycle_id,  # <-- Variable dynamique, pas la chaîne "id"
                "nom": cycle.nom,
            },
        }

    finally:
        cursor.close()
        conn.close()

#route pour supprimer un cycle
@app.delete("/supprimerCycle/{id}")
def delete_un_cycle(id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM cycle WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="cycle non trouvé")

    conn.commit()
    conn.close()

    return {"message": "cycle supprimé avec succès"}

#route pour afficher le total d'ensignants
@app.get("/total_enseignant")
def get_total_enseignant()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM enseignant")
    total_enseignant = cursor.fetchone()[0]
    return {"total_enseignant": total_enseignant}

#affichage de la liste des enseignants
@app.get("/enseignant")
def get_all_enseignant()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM enseignant")
    enseignant = cursor.fetchall()
    return {"enseignant": enseignant}

#affichage d'un enseignant par son id
@app.get("/enseignant/{nom}/{prenom}")
def get_enseignant_par_id(nom: str, prenom: str)-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM enseignant WHERE nom = %s and prenom =%s", (nom, prenom))
    enseignant = cursor.fetchone()
    if enseignant is None:
        raise HTTPException(status_code=404, detail="enseignant non trouvé")
    return {"enseignant": enseignant}

# Modèle des données attendues dans le corps de la requête (JSON)
class enseignantAjouter(BaseModel):
    nom: str
    prenom: str
    sexe: str
    date_naissance: str
    lieu_naissance: str
    adresse: str
    telephone: str
    email: str
    diplome: str
    date_embauche: str
    statut: str
   

# 2. Route POST pour ajouter un enseignant
@app.post("/ajout_enseignant")
def ajouter_enseignant(enseignant: enseignantAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO enseignant (
         nom, prenom, sexe, date_naissance, lieu_naissance, adresse, telephone, email, diplome, date_embauche, statut
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    valeurs = (
      enseignant.nom,
      enseignant.prenom,
      enseignant.sexe,
      enseignant.date_naissance,
      enseignant.lieu_naissance,
      enseignant.adresse,
      enseignant.telephone,
      enseignant.email,
      enseignant.diplome,
      enseignant.date_embauche,
      compat._statut_enseignant(enseignant.statut)
    )

    try:
        cursor.execute(sql, valeurs)
        conn.commit()
        nouvel_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return {
        "message": "enseignant ajouté avec succès",
        "id": nouvel_id,
        "enseignant": enseignant.model_dump()
    }

class enseignantModifier(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    date_naissance: Optional[str] = None
    lieu_naissance: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    diplome: Optional[str] = None
    date_embauche: Optional[str] = None
    statut: Optional[str] = None

#route pour modifier un enseignant a partir de son id
@app.put("/modifierEnseignant/{id}")
def put_un_enseignant(id: int, enseignant: enseignantModifier):
    #Extraire uniquement les champs envoyés
    nouvelles_donnees = enseignant.model_dump(exclude_unset=True)

    if not nouvelles_donnees:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier n'a été fourni")

    if "statut" in nouvelles_donnees:
        nouvelles_donnees["statut"] = compat._statut_enseignant(
            nouvelles_donnees["statut"])

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Vérifier si l'enseignant existe
    cursor.execute("SELECT id FROM enseignant WHERE id=%s", (id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Enseignant non trouvé")

    #Construire et exécuter la mise à jour dynamique
    clauses_set = [f"{cle}=%s" for cle in nouvelles_donnees.keys()]
    sql = f"UPDATE enseignant SET {', '.join(clauses_set)} WHERE id=%s"

    valeurs = list(nouvelles_donnees.values())
    valeurs.append(id)

    cursor.execute(sql, tuple(valeurs))
    conn.commit()

    #Récupérer la fiche COMPLÈTE et À JOUR de l'enseignant
    cursor.execute("SELECT * FROM enseignant WHERE id=%s", (id,))
    enseignant_mis_a_jour = cursor.fetchone()

    cursor.close()
    conn.close()

    return {"message": "enseignant modifié avec succès", "enseignant": enseignant_mis_a_jour}

#route pour supprimer un enseignant
@app.delete("/supprimerEnseignant/{nom}/{prenom}")
def delete_un_enseignant(nom: str, prenom: str):
    conn=get_connection()
    cursor = conn.cursor(buffered=True)

    #recuperer l'id de l'enseignant
    cursor.execute("select id from enseignant where nom=%s and prenom=%s", (nom, prenom))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="enseignant non trouvé")
    id_enseignant = ligne[0]

    cursor.execute("DELETE FROM enseignant WHERE id = %s", (id_enseignant,))

    conn.commit()
    conn.close()

    return {"message": "enseignant supprimé avec succès"}

#route pour afficher le total de paiements
@app.get("/total_paiement")
def get_total_paiement()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(id) FROM paiement")
    total_paiement = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    # Cle canonique + ancienne cle conservee pour compatibilite.
    return {"total_paiement": total_paiement,
            "nombre total de paiements": total_paiement}

#affichage du montant total des paiements
@app.get("/total_montant_paiement")
def get_total_montant_paiement()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    # COALESCE : SUM renvoie NULL (pas 0) quand la table est vide.
    cursor.execute("SELECT COALESCE(SUM(montant), 0) FROM paiement")
    total_montant = cursor.fetchone()[0]
    return {"total_montant_paiement": total_montant}

#affichage de la liste des paiements
@app.get("/paiement")
def get_all_paiement()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM paiement")
    paiement = cursor.fetchall()
    return {"paiement": paiement}

# Affichage du bilan des paiements par type de frais
@app.get("/paiement/bilan/type_frais")
def get_bilan_paiement_par_type() -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT 
                type_frais, 
                SUM(montant) AS total_montant
            FROM paiement 
            GROUP BY type_frais
        """
        cursor.execute(sql)
        bilan = cursor.fetchall()
        return {"bilan": bilan}

    finally:
        cursor.close()
        conn.close()

#affichage du bilan des paiements par annee scolaire
@app.get("/paiement/bilan/{annee_scolaire}")
def get_bilan_paiement_par_annee(annee_scolaire: str)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT type_frais, SUM(montant) FROM paiement, inscription, annee_scolaire WHERE paiement.inscription_id=inscription.id and inscription.annee_scolaire_id=annee_scolaire.id and  annee_scolaire.libelle like %s GROUP BY type_frais", (annee_scolaire,))
    paiement = cursor.fetchall()
    return {"paiement": paiement}

#affichage du bilan des paiements par trimestre
@app.get("/paiement/bilan/trimestre/{trimestre}")
def get_bilan_paiement_par_trimestre(trimestre: str)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT type_frais, SUM(montant) FROM paiement WHERE trimestre = %s GROUP BY type_frais", (trimestre,))
    paiement = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"paiement": paiement}

# Affichage du bilan des paiements par élève
@app.get("/paiement/bilan/eleve/{nom}/{prenom}")
def get_bilan_paiement_par_eleve(nom: str, prenom: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT 
            eleve.nom, 
            eleve.prenom, 
            paiement.type_frais, 
            SUM(paiement.montant) AS total_montant, 
            MAX(paiement.date_paiement) AS derniere_date_paiement, 
            annee_scolaire.libelle
        FROM paiement, inscription, eleve, annee_scolaire
        WHERE paiement.inscription_id=inscription.id and inscription.eleve_id=eleve.id and inscription.annee_scolaire_id=annee_scolaire.id 
        and LOWER(eleve.nom) = LOWER(%s) AND LOWER(eleve.prenom) = LOWER(%s) 
        GROUP BY eleve.nom, eleve.prenom, paiement.type_frais, annee_scolaire.libelle;
    """
    cursor.execute(sql, (nom, prenom))
    paiement = cursor.fetchall()

    cursor.close()
    conn.close()

    if not paiement:
        raise HTTPException(status_code=404, detail="Aucun paiement trouvé pour cet élève")

    return {"paiement": paiement}

#affichage du bilan des paiements par classe
@app.get("/paiement/bilan/classe/{classe}")
def get_bilan_paiement_par_classe(classe: int)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT type_frais, SUM(montant) as total_montant, classe.classe FROM paiement, classe, inscription WHERE paiement.inscription_id = inscription.id and inscription.classe_id=classe.id AND classe.id = %s GROUP BY type_frais", (classe,))
    paiement = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"paiement": paiement}

#affichage du bilan des paiements par mode de paiement
@app.get("/paiement/bilan/mode_paiement/{mode_paiement}")
def get_bilan_paiement_par_mode(mode_paiement: str)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM paiement WHERE mode_paiement = %s", (mode_paiement,))
    paiement = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"paiement": paiement}

# affichage des paiements d'un eleve
@app.get("/paiement/eleve/{nom}/{prenom}")
def get_paiement_par_eleve(nom: str, prenom: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT 
            eleve.nom, 
            eleve.prenom, 
            paiement.type_frais, 
            paiement.montant , 
            paiement.date_paiement , 
            paiement.mode_paiement
        FROM paiement, inscription, eleve
        WHERE paiement.inscription_id=inscription.id and inscription.eleve_id=eleve.id and eleve.nom = %s AND eleve.prenom = %s 
    """
    try:
        cursor.execute(sql, (nom, prenom))
        paiement = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not paiement:
        raise HTTPException(status_code=404, detail="Aucun paiement trouvé pour cet élève")

    return {"paiement": paiement}

#affichage du montant total d'une classe
@app.get("/paiement/bilan/classe/total/{classe}")
def get_total_paiement_par_classe(classe: int)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT SUM(montant) as total FROM paiement, inscription, classe WHERE paiement.inscription_id=inscription.id and inscription.classe_id=classe.id and classe_id = %s", (classe,))
    total = cursor.fetchone()
    cursor.close()
    conn.close()
    return {"total": total}

# Classe dédiée aux versements et mensualités
class PaiementVersement(BaseModel):
    inscription_id: int
    type_frais: str  # Ex: "Scolarité", "Cantine", "Transport"
    montant: float
    mode_paiement: str  # Ex: "Espèces", "Mobile Money"
    trimestre: Optional[str] = None  # Ex: "1er Trimestre"
    mois: Optional[str] = None  # Ex: "Octobre"
    uuid_client: str


# 2. Route POST pour ajouter un paiement
@app.post("/ajout_paiement")
def ajouter_paiement(paiement: PaiementVersement):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO paiement (
            inscription_id, type_frais, montant, mode_paiement, trimestre, mois, uuid_client
        ) VALUES ( %s, %s, %s, %s, %s, %s, %s)
    """

    valeurs = (
        paiement.inscription_id,
        compat._type_frais(paiement.type_frais),
        paiement.montant,
        compat._mode_paiement(paiement.mode_paiement),
        compat._trimestre(paiement.trimestre),
        paiement.mois,
        paiement.uuid_client
    )

    try:
        cursor.execute(sql, valeurs)
        conn.commit()
        nouvel_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return {
        "message": "paiement ajouté avec succès",
        "id": nouvel_id,
        "paiement": paiement.model_dump()
    }

class paiementModifier(BaseModel):
    inscription_id: Optional[int] = None
    type_frais: Optional[str] = None
    montant: Optional[float] = None
    mode_paiement: Optional[str] = None
    trimestre: Optional[str] = None
    mois: Optional[str] = None


@app.put("/modifierPaiement/{id}")
def put_un_paiement(id: int, paiement: paiementModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer le paiement existant
    cursor.execute("SELECT * FROM paiement WHERE id = %s", (id,))
    existant = cursor.fetchone()

    if existant is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Paiement non trouvé")

    # Fusionner les nouvelles données reçues avec l'existant
    nouvelles_donnees = paiement.model_dump(exclude_unset=True)
    existant.update(nouvelles_donnees)

    # Mettre à jour la table
    sql = """
        UPDATE paiement
        SET inscription_id = %s,
            type_frais = %s,
            montant = %s,
            mode_paiement = %s,
            trimestre = %s,
            mois = %s
        WHERE id = %s
    """
    valeurs = (
        existant["inscription_id"],
        existant["type_frais"],
        existant["montant"],
        compat._mode_paiement(existant["mode_paiement"]),
        compat._trimestre(existant["trimestre"]),
        existant["mois"],
        id,
    )

    cursor.execute(sql, valeurs)
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "Paiement modifié avec succès", "paiement": existant}

#route pour supprimer un paiement
@app.delete("/supprimerPaiement/{id}")
def delete_un_paiement(id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM paiement WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="paiement non trouvé")

    conn.commit()
    conn.close()

    return {"message": "paiement supprimé avec succès"}

#route pour afficher le total des notes
@app.get("/total_note")
def get_total_note()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM note")
    total_note = cursor.fetchone()[0]
    return {"total_note": total_note}

#affichage de la liste des notes
@app.get("/note")
def get_all_note()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM note")
    note = cursor.fetchall()
    return {"note": note}

#affichage des note d'un élève par son nom et prenom
@app.get("/note/eleve/{nom}/{prenom}")
def get_note_par_eleve(nom: str, prenom: str)-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT eleve.nom, eleve.prenom, eleve.sexe, classe.classe, matiere.nom, note.note, eleve.nom_parent, eleve.numero_parent FROM note, inscription, classe, eleve, matiere WHERE inscription.eleve_id = eleve.id and inscription.classe_id=classe.id and note.inscription_id=inscription.id and note.matiere_id=matiere.id and eleve.nom = %s AND eleve.prenom = %s", (nom, prenom))
    note = cursor.fetchall()
    if not note:
        raise HTTPException(status_code=404, detail="notes non trouvées")
    return {"note": note}

# Modèle des données attendues dans le corps de la requête (JSON)
class noteAjouter(BaseModel):
    inscription_id: int
    matiere_id: int
    type_evaluation: str
    note: float
    note_sur: int
    date_evaluation: date
    trimestre: str
    uuid_client: Optional[str] = None

# 2. Route POST pour ajouter une note
@app.post("/ajout_note")
def ajouter_note(note: noteAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO note (
            inscription_id, matiere_id, type_evaluation, note, note_sur, date_evaluation, trimestre, uuid_client
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    valeurs = (
        note.inscription_id,  
        note.matiere_id,      
        note.type_evaluation,
        note.note,
        note.note_sur,
        note.date_evaluation,
        compat._trimestre(note.trimestre),
        note.uuid_client
    )

    try:
        cursor.execute(sql, valeurs)
        conn.commit()
        nouvel_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return {
        "message": "note ajoutée avec succès",
        "id": nouvel_id,
        "note": note.model_dump()
    }

class noteModifier(BaseModel):
    inscription_id: Optional[int] = None
    type_evaluation: Optional[str] = None
    note: Optional[float] = None
    note_sur: Optional[int] = None
    date_evaluation: Optional[str] = None
    trimestre: Optional[str] = None
    matiere_id: Optional[int] = None


# route pour modifier une note a partir de sa matiere 
@app.put("/modifierNote/{id}")
def put_un_note(id: int, note: noteModifier):
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        UPDATE note
        SET inscription_id = COALESCE(%s, inscription_id),
            type_evaluation = COALESCE(%s, type_evaluation),
            note = COALESCE(%s, note),
            note_sur = COALESCE(%s, note_sur),
            date_evaluation = COALESCE(%s, date_evaluation),
            trimestre = COALESCE(%s, trimestre),
            matiere_id = COALESCE(%s, matiere_id)
        WHERE  id = %s
    """
    valeurs = (
        note.inscription_id,
        note.type_evaluation,
        note.note,
        note.note_sur,
        note.date_evaluation,
        compat._trimestre(note.trimestre) if note.trimestre is not None else None,
        note.matiere_id,
        id
    )

    cursor.execute(sql, valeurs)
    conn.commit()

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="note non trouvée")

    cursor.close()
    conn.close()

    return {"message": "note modifiée avec succès"}

#route pour supprimer une note
@app.delete("/supprimerNote/{id}")
def delete_un_note(id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM note WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="note non trouvée")

    conn.commit()
    conn.close()

    return {"message": "note supprimée avec succès"}

#route pour calculer la moyenne de classe d'un élève par son nom et l'afficher avec les informations de l'élève grace a la table programme
@app.get("/moyenne/{nom}/{prenom}/{type_evaluation}")
def get_moyenne_par_type_evaluation(nom: str, prenom: str, type_evaluation: str):
    conn = get_connection()
    cursor = conn.cursor( buffered=True)

    #Vérifier que l'élève existe, et le récupérer proprement
    cursor.execute("SELECT nom, prenom, sexe, classe, type_evaluation, nom_parent, numero_parent  FROM eleve, classe, inscription, note WHERE inscription.classe_id = classe.id and inscription.eleve_id = eleve.id AND note.inscription_id=inscription.id and nom = %s AND prenom = %s AND note.type_evaluation = %s", (nom, prenom, type_evaluation))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    colonnes = [d[0] for d in cursor.description]
    eleve = dict(zip(colonnes, ligne))

    #Moyenne pondérée par les coefficients
    cursor.execute("""
       SELECT SUM(note * programme.coefficient) / SUM(programme.coefficient)
        FROM note, eleve, programme, inscription, matiere
        WHERE inscription.eleve_id = eleve.id AND note.inscription_id=inscription.id
          AND note.matiere_id = matiere.id AND programme.matiere_id=matiere.id
          AND programme.classe_id = inscription.classe_id
          AND eleve.est_supprime = 0
          AND eleve.nom = %s AND eleve.prenom = %s
          AND note.type_evaluation = %s;
    """, (nom, prenom, type_evaluation))
    resultat = cursor.fetchone()
    moyenne = resultat[0] if resultat else None

    conn.close()

    return {
        "eleve": eleve,
        "moyenne": round(moyenne, 2) if moyenne is not None else None
    }

#route pour afficher le bulletin d'un élève par son nom, prénom et trimestre grace a la table programme et note, avec la moyenne de devoirs de classe et la moyenne de composition
@app.get("/bulletin/{nom}/{prenom}/{trimestre}")
def get_bulletin_par_eleve(nom: str, prenom: str, trimestre: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer l'élève, avec son ID cette fois
    cursor.execute("""
        SELECT eleve.id, eleve.nom, eleve.prenom, eleve.sexe, classe.classe AS classe
        FROM eleve, inscription, classe
        WHERE inscription.eleve_id=eleve.id and inscription.classe_id=classe.id and eleve.nom = %s AND eleve.prenom = %s
    """, (nom, prenom))
    eleve = cursor.fetchone()
    if eleve is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    eleve_id = eleve["id"]

    # Notes du trimestre
    cursor.execute("""
        SELECT DISTINCT matiere.nom, type_evaluation, note, note_sur, coefficient
        FROM note, matiere, programme, inscription, eleve
        WHERE inscription.eleve_id=eleve.id AND note.inscription_id=inscription.id
          AND note.matiere_id=matiere.id AND programme.matiere_id=matiere.id
          AND programme.classe_id = inscription.classe_id
          AND inscription.eleve_id = %s AND note.trimestre = %s
        ORDER BY matiere.nom, note.type_evaluation
    """, (eleve_id, trimestre))
    notes = cursor.fetchall()

    # Moyenne des devoirs de classe (type_evaluation "Devoir 1"/"Devoir 2"/...)
    cursor.execute("""
        SELECT SUM(note * programme.coefficient) / SUM(programme.coefficient) AS moyenne
        FROM note
        JOIN inscription ON note.inscription_id = inscription.id
        JOIN programme ON note.matiere_id = programme.matiere_id
          AND programme.classe_id = inscription.classe_id
        WHERE inscription.eleve_id = %s AND note.trimestre = %s
          AND LOWER(note.type_evaluation) LIKE 'devoir%'
    """, (eleve_id, trimestre))
    ligne_devoirs = cursor.fetchone()
    moyenne_devoirs = ligne_devoirs["moyenne"] if ligne_devoirs else None

    # Moyenne de composition
    cursor.execute("""
        SELECT SUM(note * programme.coefficient) / SUM(programme.coefficient) AS moyenne
        FROM note
        JOIN inscription ON note.inscription_id = inscription.id
        JOIN programme ON note.matiere_id = programme.matiere_id
          AND programme.classe_id = inscription.classe_id
        WHERE inscription.eleve_id = %s AND note.trimestre = %s
          AND LOWER(note.type_evaluation) = 'composition'
    """, (eleve_id, trimestre))
    ligne_composition = cursor.fetchone()
    moyenne_composition = ligne_composition["moyenne"] if ligne_composition else None

    conn.close()

    if moyenne_devoirs is not None and moyenne_composition is not None:
        moyenne = (moyenne_devoirs + 2 * moyenne_composition) / 3  # ⚠️ à confirmer avec le vrai barème de l'école
    else:
        moyenne = None

    return {
        "eleve": eleve,
        "trimestre": trimestre,
        "notes": notes,
        "moyenne": round(moyenne, 2) if moyenne is not None else None
    }

#route pour afficher le total des presences par classe
@app.get("/total_presence/{classe}")
def get_total_presence(classe: str):
    conn = get_connection()
    cursor = conn.cursor()

    #Vérifier que la classe existe
    cursor.execute("SELECT * FROM classe WHERE classe = %s", (classe,))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Classe non trouvée")

    #Compter le nombre de présences pour cette classe
    cursor.execute("""
        SELECT COUNT(*)
        FROM presences, classe
        WHERE presences.classe_id = classe.id and classe= %s
    """, (classe,))
    total_presence = cursor.fetchone()[0]

    conn.close()

    return {
        "classe": classe,
        "total_presence": total_presence
    }

#route pour afficher la liste des presences par classe
@app.get("/presence/{classe}")
def get_presence_par_classe(classe: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    #Vérifier que la classe existe
    cursor.execute("SELECT * FROM classe WHERE classe = %s", (classe,))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Classe non trouvée")

    #Récupérer la liste des présences pour cette classe
    cursor.execute("""
        SELECT *
        FROM presences, classe
        WHERE presences.classe_id = classe.id and classe=%s
    """, (classe,))
    presence = cursor.fetchall()

    conn.close()

    return {
        "classe": classe,
        "presence": presence
    }

#afficher la liste des eleves d'une classe pour remplir les presences
@app.get("/liste_de_presence_par_classe/{classe}")
def get_liste_de_presence_par_classe(classe: str):
    conn=get_connection()
    cursor=conn.cursor(dictionary=True)

    #verifie si la classe existe
    cursor.execute("SELECT * FROM classe WHERE classe = %s", (classe,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="classe non trouvée")

    #afficher la liste des eleves par classe 
    cursor.execute("select nom, prenom, sexe, classe, presences.statut from eleve left join presences on eleve.id=presences.eleve_id left join classe on presences.classe_id=classe.id where classe= %s", (classe, ))
    liste_eleve= cursor.fetchall()
    conn.close()
    return{"liste de presence par classe": liste_eleve}


#route pour ajouter une présence pour un élève dans une classe
class PresenceAjouter(BaseModel):
    eleve_id: Optional[int]=None
    statut: str  
    justifie: Optional[str] = None
    classe_id: int
    uuid_client: Optional[str] = None

@app.post("/ajout_presence")
def ajouter_presence(presence: PresenceAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Vérifier que l'élève existe
    cursor.execute("SELECT * FROM eleve WHERE id = %s", (presence.eleve_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    sql = """
        INSERT INTO presences (eleve_id, statut, justifie, classe_id)
        VALUES (%s, %s, %s, %s)
    """
    valeurs = (
        presence.eleve_id,
        compat._statut_presence(presence.statut),
        _oui_non_sql(presence.justifie),
        presence.classe_id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Présence ajoutée avec succès",
        "id": nouvel_id,
        "presence": presence.model_dump(),
    }

#modèle des données attendues dans le corps de la requête (JSON) pour modifier une présence
class PresenceModifier(BaseModel):
    eleve_id: Optional[int] = None
    statut: Optional[str] = None  
    justifie: Optional[str] = None
    classe_id: Optional[int] = None

#route pour modifier une présence pour un élève dans une classe
@app.put("/modifierPresence/{id}")
def modifier_presence(id: int, presence: PresenceModifier):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    # Récupérer la présence existante
    cursor.execute("SELECT presences.*, eleve.nom, eleve.prenom, eleve.sexe, classe.classe FROM presences, classe, eleve WHERE presences.eleve_id=eleve.id and presences.classe_id=classe.id and presences.id=%s", (id, ))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Présence non trouvée")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = presence.model_dump(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE presences
        SET eleve_id=%s, statut=%s, justifie=%s, classe_id=%s
        WHERE id =%s
    """
    valeurs = (
        donnees_actuelles["eleve_id"],
        compat._statut_presence(donnees_actuelles["statut"]),
        donnees_actuelles["justifie"],
        donnees_actuelles["classe_id"],
        id
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "Présence modifiée avec succès", "presence": donnees_actuelles}

#route pour supprimer une présence pour un élève dans une classe
@app.delete("/supprimerPresence/{id}")
def supprimer_presence(id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM presences WHERE id = %s", (id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Présence non trouvée")
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur suppression : {str(e)}")
    finally:
        cursor.close()
        conn.close()

    return {"message": "Présence supprimée avec succès"}

#route ajouter une matiere
class matiereAjouter(BaseModel):
    nom: str

@app.post("/ajout_matiere")
def ajouter_matiere(matiere: matiereAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO matiere (nom)
        VALUES (%s)
    """
    valeurs = (matiere.nom,)
    cursor.execute(sql, valeurs)
    conn.commit()
    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Matière ajoutée avec succès",
        "id": nouvel_id,
        "matiere": matiere.model_dump(),
    }

#route pour modifier une matiere
class matiereModifier(BaseModel):
    nom: Optional[str] = None

@app.put("/modifierMatiere/{id}")
def modifier_matiere(id: int, matiere: matiereModifier):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)

    # Récupérer la matière existante
    cursor.execute("SELECT * FROM matiere WHERE id=%s", (id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Matière non trouvée")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = matiere.model_dump(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE matiere
        SET nom=%s
        WHERE id=%s
    """
    valeurs = (
        donnees_actuelles["nom"],
        id
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "Matière modifiée avec succès", "matiere": donnees_actuelles}

#route pour supprimer une matiere
@app.delete("/supprimerMatiere/{id}")
def supprimer_matiere(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM matiere WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Matière non trouvée")

    conn.commit()
    conn.close()

    return {"message": "Matière supprimée avec succès"}

#route pour afficher la liste des matieres
@app.get("/matiere")
def lister_matieres():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM matiere")
    matieres = cursor.fetchall()

    conn.close()

    return {"matieres": matieres}

#route pour afficher une matiere par son id
@app.get("/matiere/{id}")
def afficher_matiere(id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM matiere WHERE id = %s", (id,))
    matiere = cursor.fetchone()

    conn.close()

    if matiere is None:
        raise HTTPException(status_code=404, detail="Matière non trouvée")

    return {"matiere": matiere}

#route pour associer une matiere a une classe et a un enseignant
class MatiereClasseEnseignant(BaseModel):
    classe_id: int
    matiere_id: int
    enseignant_id: int
    coefficient: Optional[int] = 1  # Valeur par défaut si non fournie

@app.post("/associerMatiereClasseEnseignant")
def associer_matiere_classe_enseignant(association: MatiereClasseEnseignant):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Vérifier que la classe existe
    cursor.execute("SELECT * FROM classe WHERE id = %s", (association.classe_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Classe non trouvée")

    # Vérifier que la matière existe
    cursor.execute("SELECT * FROM matiere WHERE id = %s", (association.matiere_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Matière non trouvée")

    # Vérifier que l'enseignant existe
    cursor.execute("SELECT * FROM enseignant WHERE id = %s", (association.enseignant_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Enseignant non trouvé")

    # Insérer l'association dans la table correspondante
    sql = """
        INSERT INTO programme (classe_id, matiere_id, enseignant_id, coefficient)
        VALUES (%s, %s, %s, %s)
    """
    valeurs = (
        association.classe_id,
        association.matiere_id,
        association.enseignant_id,
        association.coefficient,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Association ajoutée avec succès",
        "id": nouvel_id,
        "association": association.model_dump(),
    }

#route pour lister le programme d'une classe avec les matieres et les enseignants
@app.get("/programme/{classe}")
def lister_programme(classe: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.id, classe.classe AS classe, m.nom AS matiere, e.nom AS enseignant_nom, p.coefficient
        FROM programme p
        JOIN matiere m ON p.matiere_id = m.id
        LEFT JOIN enseignant e ON p.enseignant_id = e.id
        join classe ON p.classe_id = classe.id
        WHERE classe.classe = %s
    """, (classe,))
    programme = cursor.fetchall()

    conn.close()

    return {"programme": programme}

#modifier coefficient ou nom enseignant ou matiere d'une classe dans le programme
class ProgrammeModifier(BaseModel):
    classe_id: Optional[int] = None
    matiere_id: Optional[int] = None
    enseignant_id: Optional[int] = None
    coefficient: Optional[int] = None

@app.put("/modifierProgramme/{id}")
def modifier_programme(id: int, programme: ProgrammeModifier):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)

    # Récupérer l'association existante
    cursor.execute("SELECT * FROM programme WHERE id=%s", (id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Association non trouvée")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = programme.model_dump(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE programme
        SET classe_id=%s, matiere_id=%s, enseignant_id=%s, coefficient=%s
        WHERE id=%s
    """
    valeurs = (
        donnees_actuelles["classe_id"],
        donnees_actuelles["matiere_id"],
        donnees_actuelles["enseignant_id"],
        donnees_actuelles["coefficient"],
        id
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "Programme modifié avec succès", "programme": donnees_actuelles}

#route pour supprimer une association matiere-classe-enseignant
@app.delete("/supprimerProgramme/{id}")
def supprimer_programme(id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM programme WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return {"message": "Programme supprimé avec succès"}

#route pour creer une annee scolaire
class AnneeScolaireAjouter(BaseModel):
    libelle: str
    date_debut: date
    date_fin: date
    est_active: bool = False

@app.post("/ajouter_annee_scolaire")
def ajouter_annee_scolaire(annee_scolaire: AnneeScolaireAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Si est_active est True, désactiver les autres années scolaires
    if annee_scolaire.est_active:
        cursor.execute("UPDATE annee_scolaire SET est_active = FALSE")

    sql = """
        INSERT INTO annee_scolaire (libelle, date_debut, date_fin, est_active)
        VALUES (%s, %s, %s, %s)
    """
    valeurs = (
        annee_scolaire.libelle,
        annee_scolaire.date_debut,
        annee_scolaire.date_fin,
        annee_scolaire.est_active,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Année scolaire ajoutée avec succès",
        "id": nouvel_id,
        "annee_scolaire": annee_scolaire.model_dump(),
    }

#lister toutes les années scolaires
@app.get("/lister_annees_scolaires")
def lister_annees_scolaires():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM annee_scolaire")
    annees_scolaires = cursor.fetchall()
    conn.close()
    return {"annees_scolaires": annees_scolaires}

#route pour recuperer l'année scolaire active
@app.get("/annee_scolaire_active")
def recuperer_annee_scolaire_active():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM annee_scolaire WHERE est_active = TRUE")
    annee_scolaire_active = cursor.fetchone()
    conn.close()
    return {"annee_scolaire_active": annee_scolaire_active}

# route pour créer un tarif
class TarifScolariteCreate(BaseModel):
    classe_id: int
    frais_inscription: float  # ex: 15000.00
    montant_pension: float  # ex: 150000.00


@app.post("/ajout_tarifs-scolarite")
def creer_tarif_scolarite(tarif: TarifScolariteCreate):
    conn = get_connection()
    cursor = conn.cursor()

    try:

        #recuperer l'annee scolaire en cours
        cursor.execute("select id from annee_scolaire where est_active= true")
        ligne_annee = cursor.fetchone()

        if ligne_annee is None:
            raise HTTPException(
                status_code=400,
                detail="Aucune année scolaire active n'est définie dans la base de données.",
            )

        annee_scolaire = ligne_annee[0]

        sql = """
            INSERT INTO tarif_scolarite (classe_id, annee_scolaire_id, frais_inscription, montant_pension)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(
            sql,
            (
                tarif.classe_id,
                annee_scolaire,
                tarif.frais_inscription,
                tarif.montant_pension,
            )
        )
        conn.commit()
        tarif_id = cursor.lastrowid

        return {
            "message": "Tarif défini avec succès pour la classe.",
            "tarif_id": tarif_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Erreur (vérifiez si un tarif n'est pas déjà configuré pour cette classe) : {str(e)}",
        )
    finally:
        cursor.close()
        conn.close()

# route pour modifier un tarif existant
class TarifScolariteUpdate(BaseModel):
    frais_inscription: Optional[float] = None
    montant_pension: Optional[float] = None

@app.put("/tarifs-scolarite/{tarif_id}")
def modifier_tarif_scolarite(tarif_id: int, tarif: TarifScolariteUpdate):
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []

    if tarif.frais_inscription is not None:
        updates.append("frais_inscription = %s")
        values.append(tarif.frais_inscription)

    if tarif.montant_pension is not None:
        updates.append("montant_pension = %s")
        values.append(tarif.montant_pension)

    if not updates:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=400, detail="Aucune champ à mettre à jour."
        )

    values.append(tarif_id)
    sql = f"UPDATE tarif_scolarite SET {', '.join(updates)} WHERE id = %s"

    try:
        cursor.execute(sql, tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tarif non trouvé")
        return {"message": "Tarif de scolarité mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la mise à jour : {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()

#lister tous les tarifs de l'annee en cours
@app.get("/tarifs-scolarite")
def lister_tarifs_annee_active():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT 
            t.id AS tarif_id,
            c.id AS classe_id,
            c.classe,
            a.libelle AS annee_scolaire,
            t.frais_inscription,
            t.montant_pension,
            (t.frais_inscription + t.montant_pension) AS total_scolarite
        FROM tarif_scolarite t
        JOIN classe c ON t.classe_id = c.id
        JOIN annee_scolaire a ON t.annee_scolaire_id = a.id
        WHERE a.est_active = TRUE
    """
    cursor.execute(sql)
    tarifs = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"tarifs": tarifs}

#obtenir le tarif precis d'une classe
@app.get("/tarifs-scolarite/classe/{classe_id}")
def obtenir_tarif_classe(classe_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT 
            t.id AS tarif_id,
            c.classe,
            a.libelle AS annee_scolaire,
            t.frais_inscription,
            t.montant_pension,
            (t.frais_inscription + t.montant_pension) AS total_scolarite
        FROM tarif_scolarite t
        JOIN classe c ON t.classe_id = c.id
        JOIN annee_scolaire a ON t.annee_scolaire_id = a.id
        WHERE t.classe_id = %s AND a.est_active = TRUE
        LIMIT 1
    """
    cursor.execute(sql, (classe_id,))
    tarif = cursor.fetchone()

    cursor.close()
    conn.close()

    if not tarif:
        raise HTTPException(
            status_code=404,
            detail="Aucun tarif configuré pour cette classe sur l'année scolaire active.",
        )

    return tarif

#route pour supprimer un tarif
@app.delete("/tarifs-scolarite/{tarif_id}")
def supprimer_tarif_scolarite(tarif_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Requête de suppression
        sql = "DELETE FROM tarif_scolarite WHERE id = %s"
        cursor.execute(sql, (tarif_id,))

        # Si aucune ligne n'a été affectée, c'est que l'ID n'existait pas
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun tarif trouvé avec l'ID {tarif_id}.",
            )

        conn.commit()

        return {
            "message": f"Le tarif ID {tarif_id} a été supprimé avec succès."
        }

    except HTTPException as http_ex:
        conn.rollback()
        raise http_ex
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression du tarif : {str(e)}",
        )
    finally:
        cursor.close()
        conn.close()

#route pour calculer le reste a payer
@app.get("/inscriptions/{inscription_id}/solde")
def obtenir_solde_eleve(inscription_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Récupérer l'inscription, l'élève, la classe et le tarif correspondant
        sql_info = """
            SELECT 
                i.id AS inscription_id,
                e.nom, e.prenom,
                c.classe,
                IFNULL(t.frais_inscription, 0) AS frais_inscription,
                IFNULL(t.montant_pension, 0) AS montant_pension,
                (IFNULL(t.frais_inscription, 0) + IFNULL(t.montant_pension, 0)) AS total_a_payer
            FROM inscription i
            JOIN eleve e ON i.eleve_id = e.id
            JOIN classe c ON i.classe_id = c.id
            LEFT JOIN tarif_scolarite t ON (t.classe_id = i.classe_id AND t.annee_scolaire_id = i.annee_scolaire_id)
            WHERE i.id = %s
        """
        cursor.execute(sql_info, (inscription_id,))
        info = cursor.fetchone()

        if not info:
            raise HTTPException(
                status_code=404, detail="Inscription non trouvée."
            )

        # 2. Calculer le total des paiements déjà effectués pour cette inscription
        sql_paiements = """
            SELECT IFNULL(SUM(montant), 0) AS total_paye 
            FROM paiement 
            WHERE inscription_id = %s
        """
        cursor.execute(sql_paiements, (inscription_id,))
        res_paye = cursor.fetchone()
        total_paye = res_paye["total_paye"]

        # 3. Calcul du reste à payer
        total_a_payer = float(info["total_a_payer"])
        reste_a_payer = total_a_payer - float(total_paye)

        return {
            "inscription_id": inscription_id,
            "eleve": f"{info['nom']} {info['prenom']}",
            "classe": info["classe"],
            "total_a_payer": total_a_payer,
            "total_paye": float(total_paye),
            "reste_a_payer": reste_a_payer,
            "statut_paiement": "SOLDE" if reste_a_payer <= 0 else "EN_RETARD",
        }

    finally:
        cursor.close()
        conn.close()

#afficher le tarif mensuel d'un eleve
@app.get("/inscriptions/{inscription_id}/suivi-mensuel")
def suivi_mensuel_eleve(inscription_id: int, type_frais: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT id, montant, mois, mode_paiement, date_paiement
            FROM paiement
            WHERE inscription_id = %s AND mois IS NOT NULL
        """
        params: list = [inscription_id]
        if type_frais:
            sql += " AND type_frais = %s"
            params.append(type_frais)
        sql += " ORDER BY date_paiement ASC"
        cursor.execute(sql, params)
        paiements = cursor.fetchall()

        # Liste des mois déjà réglés
        mois_payes = [p["mois"] for p in paiements]

        return {
            "inscription_id": inscription_id,
            "type_frais": type_frais,
            "mois_regles": mois_payes,
            "details": paiements,
        }
    finally:
        cursor.close()
        conn.close()

# CONFIGURATION ET UTILITAIRES SÉCURITÉ / JWT
# Le secret est fourni par GS_JWT_SECRET ou genere/persiste dans .jwt_secret
# (voir securite.py). Aucune valeur faible n'est codee en dur.
SECRET_KEY = securite.SECRET_KEY
ALGORITHM = securite.ALGORITHM
TOKEN_EXPIRATION_SECONDS = securite.TOKEN_EXPIRATION_SECONDS


# 1. Hachage des mots de passe (Version bcrypt native)
def hacher_mot_de_passe(mot_de_passe: str) -> str:
    pwd_bytes = mot_de_passe.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe_brut: str, hash_stocke: str) -> bool:
    # Compatibilite desktop : hash PBKDF2 "salt_hex:hash_hex" (cf. db.py)
    # en plus du format bcrypt natif serveur.
    if ":" in hash_stocke:
        try:
            import hashlib
            import hmac as _hmac
            salt_hex, h_hex = hash_stocke.split(":", 1)
            calcule = hashlib.pbkdf2_hmac(
                "sha256", mot_de_passe_brut.encode("utf-8"),
                bytes.fromhex(salt_hex), 100000).hex()
            return _hmac.compare_digest(calcule, h_hex)
        except ValueError:
            return False
    pwd_bytes = mot_de_passe_brut.encode("utf-8")[:72]
    hash_bytes = hash_stocke.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


# 2. Génération du Token JWT
def creer_token_accès(data: dict) -> str:
    payload = data.copy()
    exp = time.time() + TOKEN_EXPIRATION_SECONDS
    payload.update({"exp": exp})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# MODÈLES PYDANTIC
class UtilisateurCreate(BaseModel):
    nom: str
    prenom: str
    telephone: str
    email: Optional[str] = None
    identifiant: Optional[str] = None
    mot_de_passe: str
    role: str = "gestionnaire"

class ConnexionDemande(BaseModel):
    identifiant: str  # Accepte le téléphone, l'email ou un identifiant
    mot_de_passe: str


# 1. Créer un compte utilisateur
@app.post("/ajout_utilisateurs")
def creer_utilisateur(data: UtilisateurCreate):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # on fait l'insertion classique
    mot_de_passe_hache = hacher_mot_de_passe(data.mot_de_passe)

    cursor.execute(
        """
        INSERT INTO utilisateur (nom, prenom, telephone, email, mot_de_passe, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            data.nom,
            data.prenom,
            data.telephone,
            data.email,
            mot_de_passe_hache,
            data.role,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Utilisateur créé avec succès"}

# 2b. Renouveler l'access token via refresh_token
@app.post("/refresh")
async def refresh_token(request: Request):
    """Renouvelle l'access token a partir d'un refresh token valide.

    Body JSON : {"refresh_token": "..."}
    Reponse : {"access_token": "...", "token_type": "bearer", "expires_in": ...}
    """
    import json
    body = await request.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token requis")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        payload = securite.verifier_refresh_token(refresh_token, conn)
        utilisateur_id = int(payload["sub"])
        username = payload["username"]

        # Genere nouveau couple de tokens
        tokens = securite.creer_tokens(utilisateur_id, "", username)
        # Stocke le nouveau refresh token
        securite.stocker_refresh_token(conn, utilisateur_id, tokens["refresh_token"])

        return {"access_token": tokens["access_token"],
                "token_type": "bearer",
                "expires_in": tokens["expires_in"]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()

# 2. Se connecter (Login)
@app.post("/login")
async def connexion(credentials: ConnexionDemande, request: Request):
    adresse_ip = request.client.host if request.client else None
    securite.limiteur_connexion.verifier(adresse_ip, credentials.identifiant)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    def _echec(code, detail, action_audit="connexion_echouee"):
        securite.limiteur_connexion.enregistrer_echec(adresse_ip, credentials.identifiant)
        try:
            compat.enregistrer_audit(cursor, None, action_audit,
                                     credentials.identifiant, adresse_ip)
            conn.commit()
        except Exception:
            conn.rollback()
        raise HTTPException(status_code=code, detail=detail)

    try:
        sql = """
            SELECT id, nom, prenom, telephone, email, mot_de_passe, role, statut 
            FROM utilisateur 
            WHERE telephone = %s OR email = %s OR identifiant = %s
        """
        cursor.execute(
            sql,
            (
                credentials.identifiant,
                credentials.identifiant,
                credentials.identifiant,
            ),
        )
        user = cursor.fetchone()

        if not user:
            return _echec(
                401,
                "Identifiant (téléphone/email) ou mot de passe incorrect.",
            )

        if user["statut"] != "actif":
            return _echec(403, "Ce compte a été suspendu ou désactivé.")

        if not verifier_mot_de_passe(credentials.mot_de_passe, user["mot_de_passe"]):
            return _echec(
                401,
                "Identifiant (téléphone/email) ou mot de passe incorrect.",
            )

        securite.limiteur_connexion.reinitialiser(adresse_ip, credentials.identifiant)
        compat.enregistrer_audit(cursor, user["id"], "connexion_reussie",
                                 credentials.identifiant, adresse_ip)
        conn.commit()

        # Genere access + refresh tokens
        tokens = securite.creer_tokens(user["id"], user["role"], user.get("identifiant") or user["telephone"])
        # Stocke le refresh token en base
        securite.stocker_refresh_token(conn, user["id"], tokens["refresh_token"])

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "expires_in": tokens["expires_in"],
            "utilisateur": {
                "id": user["id"],
                "nom": user["nom"],
                "prenom": user["prenom"],
                "telephone": user["telephone"],
                "role": user["role"],
            },
        }

    finally:
        cursor.close()
        conn.close()


# 3. Lister les comptes utilisateurs
@app.get("/utilisateurs")
def lister_utilisateurs():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT id, nom, prenom, telephone, email, role, statut, updated_at AS date_creation 
            FROM utilisateur 
            ORDER BY nom ASC
        """
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@app.get("/comptes-syndication")
def comptes_syndication(request: Request):
    """Comptes utilisateurs avec identifiant et hash de mot de passe, pour
    que chaque poste puisse proposer le meme login (multi-poste).
    Protégé par secret de syndication quand GS_SYNC_SECRET est configuré."""
    from server import securite
    secret = request.headers.get("x-sync-secret", "")
    if not securite.sync_autorisee(secret):
        raise HTTPException(status_code=403, detail="Secret de syndication invalide")
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, nom, prenom, telephone, email, identifiant,
                   mot_de_passe, role, statut
            FROM utilisateur
            ORDER BY nom ASC, prenom ASC
        """)
        return {"comptes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.put("/comptes/{identifiant}")
def modifier_compte(identifiant: int, data: UtilisateurCreate):
    """Modifie un compte utilisateur (nom, prenom, telephone, email, role, mot_de_passe optionnel)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verifie que le compte existe
        cursor.execute("SELECT id FROM utilisateur WHERE id = %s", (identifiant,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Compte non trouve")

        updates = []
        params = []
        if data.nom:
            updates.append("nom = %s")
            params.append(data.nom)
        if data.prenom:
            updates.append("prenom = %s")
            params.append(data.prenom)
        if data.telephone:
            # Verifie unicite telephone
            cursor.execute("SELECT id FROM utilisateur WHERE telephone = %s AND id != %s",
                           (data.telephone, identifiant))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Telephone deja utilise")
            updates.append("telephone = %s")
            params.append(data.telephone)
        if data.email is not None:
            updates.append("email = %s")
            params.append(data.email)
        if data.identifiant is not None:
            updates.append("identifiant = %s")
            params.append(data.identifiant)
        if data.role:
            updates.append("role = %s")
            params.append(data.role)
        if data.mot_de_passe:
            updates.append("mot_de_passe = %s")
            params.append(hacher_mot_de_passe(data.mot_de_passe))
            # Revoque les refresh tokens existants (securite)
            securite.revoquer_tous_refresh_tokens(conn, identifiant)

        if not updates:
            raise HTTPException(status_code=400, detail="Aucun champ a modifier")

        params.append(identifiant)
        cursor.execute(
            f"UPDATE utilisateur SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            params)
        conn.commit()
        return {"message": "Compte modifie avec succes"}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.put("/comptes/{identifiant}/actif")
def toggle_compte_actif(identifiant: int, actif: bool):
    """Active/desactive un compte utilisateur."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM utilisateur WHERE id = %s", (identifiant,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Compte non trouve")

        cursor.execute(
            "UPDATE utilisateur SET statut = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            ("actif" if actif else "inactif", identifiant))
        conn.commit()

        # Si desactive, revoque tous les refresh tokens
        if not actif:
            securite.revoquer_tous_refresh_tokens(conn, identifiant)

        return {"message": f"Compte {'active' if actif else 'desactive'} avec succes"}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.put("/comptes/{identifiant}/reset-password")
def reset_compte_password(identifiant: int, nouveau_mot_de_passe: str):
    """Reinitialise le mot de passe d'un compte."""
    if not nouveau_mot_de_passe or len(nouveau_mot_de_passe) < 6:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (min 6 caracteres)")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM utilisateur WHERE id = %s", (identifiant,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Compte non trouve")

        cursor.execute(
            "UPDATE utilisateur SET mot_de_passe = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (hacher_mot_de_passe(nouveau_mot_de_passe), identifiant))
        conn.commit()

        # Revoque tous les refresh tokens (securite)
        securite.revoquer_tous_refresh_tokens(conn, identifiant)

        return {"message": "Mot de passe reinitialise avec succes"}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.delete("/comptes/{identifiant}")
def supprimer_compte(identifiant: int):
    """Supprime un compte utilisateur."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM utilisateur WHERE id = %s", (identifiant,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Compte non trouve")

        # Supprime les refresh tokens lies
        cursor.execute("DELETE FROM refresh_tokens WHERE utilisateur_id = %s", (identifiant,))
        cursor.execute("DELETE FROM utilisateur WHERE id = %s", (identifiant,))
        conn.commit()
        return {"message": "Compte supprime avec succes"}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


# ---------- Routes de syndication pour le pull multi-poste ----------

@app.get("/lister_toutes_les_inscriptions")
def lister_toutes_les_inscriptions():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT i.id, i.eleve_id, i.classe_id, i.annee_scolaire_id,
                   i.date_inscription, i.statut, i.uuid_client,
                   e.nom, e.prenom, e.uuid_client AS eleve_uuid,
                   c.classe AS classe_nom, a.libelle AS annee_scolaire
            FROM inscription i
            JOIN eleve e ON e.id = i.eleve_id
            JOIN classe c ON c.id = i.classe_id
            JOIN annee_scolaire a ON a.id = i.annee_scolaire_id
        """)
        return {"inscriptions": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/toutes_presence")
def toutes_presence():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.id, p.eleve_id, p.classe_id, p.date_presence,
                   p.statut, p.justifie, p.uuid_client,
                   e.nom, e.prenom, e.uuid_client AS eleve_uuid,
                   c.classe AS classe_nom
            FROM presences p
            JOIN eleve e ON e.id = p.eleve_id
            JOIN classe c ON c.id = p.classe_id
        """)
        return {"presences": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/tous_les_programme")
def tous_les_programme():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT pr.id, pr.classe_id, pr.matiere_id, pr.enseignant_id,
                   pr.coefficient,
                   c.classe AS classe_nom,
                   m.nom AS matiere_nom,
                   COALESCE(en.nom, '') AS enseignant_nom,
                   COALESCE(en.prenom, '') AS enseignant_prenom
            FROM programme pr
            JOIN classe c ON c.id = pr.classe_id
            JOIN matiere m ON m.id = pr.matiere_id
            LEFT JOIN enseignant en ON en.id = pr.enseignant_id
        """)
        return {"programmes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/paiement-syndication")
def paiement_syndication():
    """Paiements avec les cles naturelles client (eleve_uuid, classe_nom)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT pay.*, e.nom, e.prenom, e.uuid_client AS eleve_uuid,
                   c.classe AS classe_nom, a.libelle AS annee_scolaire
            FROM paiement pay
            JOIN inscription i ON i.id = pay.inscription_id
            JOIN eleve e ON e.id = i.eleve_id
            JOIN classe c ON c.id = i.classe_id
            LEFT JOIN annee_scolaire a ON a.id = i.annee_scolaire_id
        """)
        return {"paiements": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/note-syndication")
def note_syndication():
    """Notes avec les cles naturelles client (eleve_uuid, matiere_nom)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT n.id, n.matiere_id, n.type_evaluation, n.note, n.note_sur,
                   n.date_evaluation, n.trimestre, n.uuid_client,
                   e.uuid_client AS eleve_uuid, e.nom, e.prenom,
                   m.nom AS matiere_nom
            FROM note n
            JOIN inscription i ON i.id = n.inscription_id
            JOIN eleve e ON e.id = i.eleve_id
            JOIN matiere m ON m.id = n.matiere_id
        """)
        return {"notes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


#route pour savoir si le pc1 ou 2 est connecte au reseau
@app.get("/ping")
def ping():
    return {"status": "online"}


class BatimentPoste(BaseModel):
    uuid_poste: str
    nom_poste: str = ""
    adresse_ip: str = ""
    version_app: str = ""
    systeme: str = ""
    est_hote: bool = False


@app.post("/present")
def declarer_poste(request: Request, donnees: BatimentPoste):
    """Battement de coeur d'un poste du reseau de l'ecole.

    Chaque poste s'annonce regulierement : le serveur conserve sa fiche
    (identite, version, systeme) et met a jour son « derniere_seen ».
    C'est la source de verite de la page « Reseau des postes »."""
    secret = request.headers.get("x-sync-secret", "")
    if not securite.sync_autorisee(secret):
        raise HTTPException(status_code=403, detail="Secret de syndication invalide")
    uuid = (donnees.uuid_poste or "").strip()
    if not uuid or len(uuid) > 64:
        raise HTTPException(status_code=400, detail="uuid_poste invalide")
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT uuid_poste FROM poste_presence WHERE uuid_poste = %s", (uuid,))
        existe = cursor.fetchone() is not None
        nom = (donnees.nom_poste or "")[:120]
        ip = ""
        if donnees.adresse_ip:
            ip = donnees.adresse_ip[:45]
        elif request.client and request.client.host:
            ip = request.client.host[:45]
        version = (donnees.version_app or "")[:20]
        systeme = (donnees.systeme or "")[:80]
        hote = 1 if donnees.est_hote else 0
        if existe:
            cursor.execute(
                "UPDATE poste_presence SET nom_poste = %s, adresse_ip = %s,"
                " version_app = %s, systeme = %s, est_hote = %s,"
                " derniere_seen = CURRENT_TIMESTAMP WHERE uuid_poste = %s",
                (nom, ip, version, systeme, hote, uuid))
        else:
            cursor.execute(
                "INSERT INTO poste_presence"
                " (uuid_poste, nom_poste, adresse_ip, version_app, systeme, est_hote)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (uuid, nom, ip, version, systeme, hote))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return {"ok": True, "uuid_poste": uuid}


@app.get("/mise-a-jour/etat")
def etat_mise_a_jour(request: Request):
    """Consigne de mise a jour du serveur central (option B).

    Le directeur peut imposer/diffuser une version aux postes en ecrivant
    `data_dir()/mise_a_jour.json` (via services.updater.ecrire_consigne) et
    en deposant les paquets dans `data_dir()/mises_a_jour_paquets/`. Chaque
    poste interroge cet endpoint avant GitHub et se met a jour depuis le LAN
    (fonctionne sans Internet).

    Json attendu (ecrit par l'app sur le poste hote) :
        {"actif": true, "version": "1.6.2", "obligatoire": false,
         "paquet_linux": "gestion-scolaire_1.6.2_amd64.deb",
         "paquet_windows": "GestionScolaire-Setup-1.6.2.exe",
         "sha256": {"<nom>": "<hex>"}}
    """
    secret = request.headers.get("x-sync-secret", "")
    if not securite.sync_autorisee(secret):
        raise HTTPException(status_code=403, detail="Secret de syndication invalide")
    try:
        from core.config import data_dir
        fichier = data_dir() / "mise_a_jour.json"
        import json as _json_maj
        consigne = _json_maj.loads(fichier.read_text(encoding="utf-8"))
        if not isinstance(consigne, dict):
            consigne = {}
    except Exception:
        consigne = {}
    actif = bool(consigne.get("actif")) and bool(consigne.get("version"))
    if not actif:
        return {"actif": False}
    return {
        "actif": True,
        "version": str(consigne.get("version")),
        "obligatoire": bool(consigne.get("obligatoire")),
        "paquet_linux": str(consigne.get("paquet_linux") or ""),
        "paquet_windows": str(consigne.get("paquet_windows") or ""),
        "sha256": consigne.get("sha256") if isinstance(consigne.get("sha256"), dict) else {},
    }


@app.get("/mise-a-jour/paquet/{nom_paquet}")
def telecharger_paquet_serveur(nom_paquet: str, request: Request):
    """Sert un paquet d'installation du depot central (LAN)."""
    secret = request.headers.get("x-sync-secret", "")
    if not securite.sync_autorisee(secret):
        raise HTTPException(status_code=403, detail="Secret de syndication invalide")
    from fastapi.responses import FileResponse
    from pathlib import Path as _Path
    try:
        from core.config import data_dir
        dossier = data_dir() / "mises_a_jour_paquets"
    except Exception:
        raise HTTPException(status_code=500, detail="Depot indisponible")
    chemin = dossier / _Path(nom_paquet).name   # anti traversee de repertoire
    if not chemin.is_file():
        raise HTTPException(status_code=404, detail="Paquet introuvable sur le depot")
    return FileResponse(str(chemin), filename=chemin.name)


def _age_presence(horodatage):
    """Age en secondes d'un « derniere_seen » recu du serveur (UTC)."""
    if not horodatage:
        return None
    import datetime as _dt
    try:
        valeur = _dt.datetime.strptime(str(horodatage)[:19],
                                       "%Y-%m-%d %H:%M:%S")
        valeur = valeur.replace(tzinfo=_dt.timezone.utc)
        return max(0, int((_dt.datetime.now(_dt.timezone.utc) - valeur)
                          .total_seconds()))
    except ValueError:
        return None


@app.get("/postes")
def liste_postes(request: Request):
    """Liste des postes connus : identite, version, derniere activite et
    etat en ligne (activite < 120 s). Utilisee par la page « Reseau »."""
    secret = request.headers.get("x-sync-secret", "")
    if not securite.sync_autorisee(secret):
        raise HTTPException(status_code=403, detail="Secret de syndication invalide")
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT uuid_poste, nom_poste, adresse_ip, version_app, systeme,
                   est_hote, premiere_seen, derniere_seen
            FROM poste_presence
            ORDER BY derniere_seen DESC
        """)
        lignes = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    for ligne in lignes:
        ligne["age_secondes"] = _age_presence(ligne.get("derniere_seen"))
    return {"postes": lignes}


@app.get("/eleve-supprimes-syndication")
def eleve_supprimes_syndication():
    """UUID des eleves supprimes/archives cote serveur, pour que chaque
    poste puisse supprimer ses copies locales (tombstone propagation)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT uuid_client FROM eleve WHERE est_supprime = TRUE"
            " AND uuid_client IS NOT NULL AND uuid_client != ''")
        return {"supprimes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/note-supprimes-syndication")
def note_supprimes_syndication():
    """UUID des notes supprimes/archives cote serveur (tombstone)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT uuid_client FROM note WHERE est_supprime = TRUE"
            " AND uuid_client IS NOT NULL AND uuid_client != ''")
        return {"supprimes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/paiement-supprimes-syndication")
def paiement_supprimes_syndication():
    """UUID des paiements supprimes/archives cote serveur (tombstone)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT uuid_client FROM paiement WHERE est_supprime = TRUE"
            " AND uuid_client IS NOT NULL AND uuid_client != ''")
        return {"supprimes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.get("/presence-supprimes-syndication")
def presence_supprimes_syndication():
    """UUID des presences supprimees/archivees cote serveur (tombstone)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT uuid_client FROM presences WHERE est_supprime = TRUE"
            " AND uuid_client IS NOT NULL AND uuid_client != ''")
        return {"supprimes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@app.post("/fermer-annee-scolaire")
async def fermer_annee_scolaire(request: Request):
    """Ferme l'année scolaire en cours et ouvre la suivante (appelée par le directeur).

    Body JSON :
    {
        "annee_archivee_id": <id de l'année à archiver>,
        "nouvelle_annee": {
            "libelle": "2026-2027",
            "date_debut": "2026-09-01",
            "date_fin": "2027-06-30",
            "promouvoir_eleves": true
        }
    }
    """
    from pydantic import BaseModel
    from typing import Optional
    import json

    class NouvelleAnnee(BaseModel):
        libelle: str
        date_debut: str
        date_fin: str
        promouvoir_eleves: bool = False

    class Payload(BaseModel):
        annee_archivee_id: int
        nouvelle_annee: NouvelleAnnee

    # Parse body manually (FastAPI dependency injection would require async)
    body = json.loads((await request.body()).decode())
    payload = Payload(**body)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Archive l'année courante
        cursor.execute(
            "UPDATE annee_scolaire SET est_active = 0, archivee = 1 WHERE id = %s",
            (payload.annee_archivee_id,))

        # 2. Crée la nouvelle année
        cursor.execute(
            """INSERT INTO annee_scolaire (libelle, date_debut, date_fin, est_active, archivee)
               VALUES (%s, %s, %s, 1, 0)""",
            (payload.nouvelle_annee.libelle, payload.nouvelle_annee.date_debut,
             payload.nouvelle_annee.date_fin))
        nouvelle_id = cursor.lastrowid

        # 3. Promeut les élèves si demandé
        if payload.nouvelle_annee.promouvoir_eleves:
            # Mapping de progression des classes
            progression = {
                "CP1": "CP2", "CP2": "CE1", "CE1": "CE2", "CE2": "CM1",
                "CM1": "CM2", "CM2": "6eme", "6eme": "5eme", "5eme": "4eme",
                "4eme": "3eme", "3eme": "2nde", "2nde": "1ere", "1ere": "Terminale"
            }
            # Pour chaque élève, trouve sa classe actuelle et la promeut
            cursor.execute(
                """SELECT e.id, c.classe FROM eleve e
                   JOIN inscription i ON i.eleve_id = e.id
                   JOIN classe c ON c.id = i.classe_id
                   WHERE i.annee_scolaire_id = %s""",
                (payload.annee_archivee_id,))
            eleves = cursor.fetchall()
            for eleve in eleves:
                classe_actuelle = eleve.get("classe")
                if classe_actuelle in progression:
                    nouvelle_classe_nom = progression[classe_actuelle]
                    cursor.execute(
                        "SELECT id FROM classe WHERE classe = %s",
                        (nouvelle_classe_nom,))
                    res = cursor.fetchone()
                    if res:
                        nouvelle_classe_id = res[0]
                        cursor.execute(
                            """UPDATE inscription SET classe_id = %s
                               WHERE eleve_id = %s AND annee_scolaire_id = %s""",
                            (nouvelle_classe_id, eleve["id"], nouvelle_id))

        conn.commit()
        return {"nouvelle_annee_id": nouvelle_id, "message": "Année fermée avec succès"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()