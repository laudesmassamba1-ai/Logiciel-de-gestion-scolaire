from fastapi import FastAPI, Path, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
import mysql.connector
import time
from typing import Optional
import jwt
import bcrypt
from passlib.context import CryptContext

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Josias50",
        database="ecole"
    )

@app.on_event("startup")
def initialiser_base_au_demarrage():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Josias50"
    )
    cursor = conn.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS ecole")
    cursor.execute("USE ecole")

    with open("schema.sql", "r", encoding="utf-8") as f:
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
            if err.errno != 1050:  # 1050 = table déjà existante, on ignore sans planter
                raise

    conn.commit()
    cursor.close()
    conn.close()
    print(" Base de données vérifiée/créée avec succès au démarrage.")

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    # On convertit en bytes et on tronque à 72 octets max pour éviter tout blocage
    pwd_bytes = mot_de_passe.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe_brut: str, hash_stocke: str) -> bool:
    pwd_bytes = mot_de_passe_brut.encode("utf-8")[:72]
    hash_bytes = hash_stocke.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)

#affichage du nombre total d'élèves
@app.get("/total_eleves")
def get_total_eleves()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM eleve")
    total_eleves = cursor.fetchone()[0]
    return {"total_eleves": total_eleves}

# afficher le nombre total d'eleves par sexe 
@app.get("/total_eleve_par_sexe")
def get_total_eleve_par_sexe() -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # Retourne les résultats sous forme de dictionnaires
    try:
        # On sélectionne aussi la colonne 'sexe'
        cursor.execute("SELECT sexe, COUNT(*) AS total FROM eleve GROUP BY sexe")
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
            WHERE classe.classe LIKE %s
        """
        cursor.execute(sql_count, (motif,))
        total_eleves = cursor.fetchone()[0]

        # 2. Récupérer le vrai nom de la classe
        cursor.execute(
            "SELECT classe FROM classe WHERE classe LIKE %s LIMIT 1", (motif,)
        )
        res_classe = cursor.fetchone()

        nom_classe = res_classe[0] if res_classe else recherche

        return {"nombre total d'élèves": {nom_classe: total_eleves}}

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
        cursor.execute("SELECT classe, COUNT(*) AS total FROM eleve, classe, inscription where eleve.id=inscription.eleve_id and inscription.classe_id=classe.id GROUP BY classe")
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
            "SELECT sexe, COUNT(*) AS total FROM eleve, classe, inscription WHERE eleve.id=inscription.eleve_id and inscription.classe_id=classe.id and classe = %s GROUP BY sexe",
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
    cursor.execute("SELECT nom, prenom, sexe FROM eleve, inscription, classe where inscription.classe_id=classe.id and inscription.eleve_id=eleve.id and  classe.classe = %s and est_supprime = 0",(classe, ))
    eleves = cursor.fetchall()
    return {"eleves": eleves}

#affchage de la liste de tous les eleves
@app.get("/eleve")
def get_all_eleves()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT eleve.id, nom, prenom, sexe, classe FROM eleve, inscription, classe where inscription.classe_id=classe.id and inscription.eleve_id=eleve.id and est_supprime = false")
    eleves = cursor.fetchall()
    return {"eleves": eleves}

#affichage d'un élève par son nom
@app.get("/eleve_recherche")
def get_eleve_par_son_nom(recherche: Optional[str]=None, recherche1: Optional[str]=None)-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if recherche:
        sql="""select eleve.id, nom, prenom, sexe,  classe, date_naissance, lieu_naissance, adresse, nom_parent, redoublant, eleve.statut, numero_parent from eleve, classe, inscription where inscription.classe_id=classe.id and inscription.eleve_id=eleve.id and nom like  %s and prenom like %s"""
        motif=f"%{recherche}%"
        motif1=f"%{recherche1}%"
        cursor.execute(sql, (motif, motif1))

    else:
        sql="""select eleve.id, nom, prenom, sexe, date_naissance, lieu_naissance, adresse, nom_parent, redoublant, statut, numero_parent, classe from eleve, classe where eleve.classe_id=classe.id"""
        cursor.execute(sql)

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
            eleve.sexe,
            eleve.date_naissance,
            eleve.lieu_naissance,
            eleve.adresse,
            eleve.nom_parent,
            eleve.redoublant,
            eleve.statut,
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
            raise Exception("Aucune année scolaire active n'a été trouvée.")

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
            paiement.type_frais,
            paiement.montant,
            paiement.mode_paiement,
            paiement.trimestre,
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
    nouvelles_donnees = eleve.dict(exclude_unset=True)

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

        # 3. Mise à jour dynamique de la table 'eleve'
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

    # On restaure l'élève en le démarquant comme non-supprimé
    cursor.execute("UPDATE eleve SET est_supprime = FALSE WHERE nom = %s and prenom=%s", (nom, prenom))
    conn.commit()

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
    cursor.execute("SELECT classe, cycle.nom FROM classe, cycle where classe.cycle_id=cycle.id")
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

    cursor.execute(sql, valeurs)
    conn.commit()

    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "classe ajoutée avec succès",
        "id": nouvel_id,
        "classe": classe.dict()
    }

class ClasseModifier(BaseModel):
    classe: Optional[str] = None
    cycle_id: Optional[int] = None

#route pour modifier une classe
@app.put("/classe/{classe_id}")
def put_une_classe(classe_id: int, classe_data: ClasseModifier):
    # Récupère UNIQUEMENT les champs envoyés dans Swagger/Postman
    nouvelles_donnees = classe_data.dict(exclude_unset=True)

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

    cursor.execute(sql, valeurs)
    conn.commit()

    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "cycle ajouté avec succès",
        "id": nouvel_id,
        "cycle": cycle.dict()
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
      enseignant.statut
    )

    cursor.execute(sql, valeurs)
    conn.commit()

    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "enseignant ajouté avec succès",
        "id": nouvel_id,
        "enseignant": enseignant.dict()
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
    nouvelles_donnees = enseignant.dict(exclude_unset=True)

    if not nouvelles_donnees:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier n'a été fourni")

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
    id_enseignant=cursor.fetchone()[0]

    cursor.execute("DELETE FROM enseignant WHERE id = %s", (id_enseignant,))

    if id_enseignant == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="enseignant non trouvé")

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
    return { "nombre total de paiements": total_paiement}

#affichage du montant total des paiements
@app.get("/total_montant_paiement")
def get_total_montant_paiement()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(montant) FROM paiement")
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
    cursor.execute(sql, (nom, prenom))
    paiement = cursor.fetchall()

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
        paiement.type_frais,
        paiement.montant,
        paiement.mode_paiement,
        paiement.trimestre,
        paiement.mois,
        paiement.uuid_client
    )

    cursor.execute(sql, valeurs)
    conn.commit()

    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "paiement ajouté avec succès",
        "id": nouvel_id,
        "paiement": paiement.dict()
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
    nouvelles_donnees = paiement.dict(exclude_unset=True)
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
        existant["mode_paiement"],
        existant["trimestre"],
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
        note.trimestre,
        note.uuid_client
    )

    cursor.execute(sql, valeurs)
    conn.commit()

    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "note ajoutée avec succès",
        "id": nouvel_id,
        "note": note.dict()
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
        note.trimestre,
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
        WHERE inscription.eleve_id = eleve.id AND note.inscription_id=inscription.id and note.matiere_id = matiere.id and programme.matiere_id=matiere.id AND eleve.nom = %s AND eleve.prenom = %s AND note.type_evaluation = %s;
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
        SELECT matiere.nom, type_evaluation, note, note_sur, coefficient
        FROM note, matiere, programme, inscription, eleve
        WHERE inscription.eleve_id=eleve.id and note.inscription_id=inscription.id and note.matiere_id=matiere.id and programme.matiere_id=matiere.id and eleve_id = %s AND trimestre = %s
    """, (eleve_id, trimestre))
    notes = cursor.fetchall()

    # Moyenne des devoirs de classe
    cursor.execute("""
        SELECT SUM(note * programme.coefficient) / SUM(programme.coefficient) AS moyenne
        FROM note
        JOIN programme ON note.programme_id = programme.id
        WHERE eleve_id = %s AND trimestre = %s AND type_evaluation = 'devoir de classe'
    """, (eleve_id, trimestre))
    moyenne_devoirs = cursor.fetchone()["moyenne"]

    # Moyenne de composition
    cursor.execute("""
        SELECT SUM(note * programme.coefficient) / SUM(programme.coefficient) AS moyenne
        FROM note
        JOIN programme ON note.programme_id = programme.id
        WHERE eleve_id = %s AND trimestre = %s AND type_evaluation = 'composition'
    """, (eleve_id, trimestre))
    moyenne_composition = cursor.fetchone()["moyenne"]

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
    cursor.execute("select nom, prenom, sexe, classe, presences.statut from eleve, presences, classe where eleve.id=presences.eleve_id and presences.classe_id=classe.id and classe= %s", (classe, ))
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
        presence.statut,
        presence.justifie,
        presence.classe_id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Présence ajoutée avec succès",
        "id": nouvel_id,
        "presence": presence.dict(),
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
    nouvelles_donnees = presence.dict(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE presences
        SET eleve_id=%s, statut=%s, justifie=%s, classe_id=%s
        WHERE id =%s
    """
    valeurs = (
        donnees_actuelles["eleve_id"],
        donnees_actuelles["statut"],
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

    cursor.execute("DELETE FROM presences WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Présence non trouvée")

    conn.commit()
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
        "matiere": matiere.dict(),
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
    nouvelles_donnees = matiere.dict(exclude_unset=True)
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
        "association": association.dict(),
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
        JOIN enseignant e ON p.enseignant_id = e.id
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
    nouvelles_donnees = programme.dict(exclude_unset=True)
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
        "annee_scolaire": annee_scolaire.dict(),
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
        annee_scolaire=cursor.fetchone()[0]

        if not annee_scolaire:
            raise HTTPException(
                status_code=400,
                detail="Aucune année scolaire active n'est définie dans la base de données.",
            )

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
        return {"message": "Tarif de scolarité mis à jour avec succès"}
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

    return tarifs

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
def suivi_mensuel_eleve(inscription_id: int, type_frais: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT id, montant, mois, mode_paiement, date_paiement
            FROM paiement
            WHERE inscription_id = %s AND type_frais = %s AND mois IS NOT NULL
            ORDER BY date_paiement ASC
        """
        cursor.execute(sql, (inscription_id, type_frais))
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
SECRET_KEY = "MON_SECRET_SUPER_SECURISE_A_CHANGER_EN_PROD_123456789"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = 8 * 3600  # 8 heures


# 1. Hachage des mots de passe (Version bcrypt native)
def hacher_mot_de_passe(mot_de_passe: str) -> str:
    pwd_bytes = mot_de_passe.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe_brut: str, hash_stocke: str) -> bool:
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

# 2. Se connecter (Login)
@app.post("/login")
def connexion(credentials: ConnexionDemande):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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
            raise HTTPException(
                status_code=401,
                detail="Identifiant (téléphone/email) ou mot de passe incorrect.",
            )

        if user["statut"] != "actif":
            raise HTTPException(
                status_code=403, detail="Ce compte a été suspendu ou désactivé."
            )

        if not verifier_mot_de_passe(credentials.mot_de_passe, user["mot_de_passe"]):
            raise HTTPException(
                status_code=401,
                detail="Identifiant (téléphone/email) ou mot de passe incorrect.",
            )

        token_payload = {
            "user_id": user["id"],
            "telephone": user["telephone"],
            "role": user["role"],
        }
        access_token = creer_token_accès(token_payload)

        return {
            "access_token": access_token,
            "token_type": "bearer",
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
            SELECT id, nom, prenom, telephone, email, role, statut, date_creation 
            FROM utilisateur 
            ORDER BY nom ASC
        """
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

#route pour savoir si le pc1 ou 2 est connecte au reseau
@app.get("/ping")
def ping():
    return {"status": "online"}