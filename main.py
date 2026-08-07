from fastapi import FastAPI, Path, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI()
conn = sqlite3.connect("ecole.db") 

#affichage du nombre total d'élèves
@app.get("/total_eleves")
def get_total_eleves()-> dict:
    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM eleve")
    total_eleves = cursor.fetchone()[0]
    return {"total_eleves": total_eleves}

#affichage de la liste des élèves
@app.get("/eleve")
def get_all_eleves()-> dict:
    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM eleve")
    eleves = cursor.fetchall()
    return {"eleves": eleves}

#affichage d'un élève par son id
@app.get("/eleve/{id}")
def get_eleve_by_id(id: int = Path(ge=1))-> dict:

    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM eleve WHERE id = ?", (id,))
    eleve = cursor.fetchone()
    if eleve is None:
        raise HTTPException(status_code=404, detail="Élève non trouvé")
    return {"eleve": eleve}

# 1. Modèle des données attendues dans le corps de la requête (JSON)
class Eleveajouter(BaseModel):
    matricule: str
    nom: str
    prenom: str
    sexe: str
    date_naissance: str
    lieu_naissance: str
    adresse: str
    nom_parent: str
    redoublant: str  # 0 pour Non, 1 pour Oui
    statut: str
    classe_id: int
    telephone_parent: str


# 2. Route POST pour ajouter l'élève
@app.post("/eleve")
def ajouter_eleve(eleve: Eleveajouter):
    conn = sqlite3.connect("ecole.db")
    cursor = conn.cursor()

    sql = """
        INSERT INTO eleve (
            matricule, nom, prenom, sexe, date_naissance,
            lieu_naissance, adresse, nom_parent,
            redoublant, statut, classe_id, numero_parent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    valeurs = (
        eleve.matricule,
        eleve.nom,
        eleve.prenom,
        eleve.sexe,
        eleve.date_naissance,
        eleve.lieu_naissance,
        eleve.adresse,
        eleve.nom_parent,
        eleve.redoublant,
        eleve.statut,
        eleve.classe_id,
        eleve.telephone_parent,
    )

    cursor.execute(sql, valeurs)
    conn.commit()

    nouvel_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Élève ajouté avec succès",
        "id": nouvel_id,
        "eleve": eleve.dict()
    }