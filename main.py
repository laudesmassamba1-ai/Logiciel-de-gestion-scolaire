from fastapi import FastAPI, Path, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

app = FastAPI()

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
def get_eleve_par_id(id: int = Path(ge=1))-> dict:

    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM eleve WHERE id = ?", (id,))
    eleve = cursor.fetchone()
    if eleve is None:
        raise HTTPException(status_code=404, detail="Élève non trouvé")
    return {"eleve": eleve}

# Modèle des données attendues dans le corps de la requête (JSON)
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

class EleveModifier(BaseModel):
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    date_naissance: Optional[str] = None
    lieu_naissance: Optional[str] = None
    adresse: Optional[str] = None
    nom_parent: Optional[str] = None
    redoublant: Optional[str] = None
    statut: Optional[str] = None
    classe_id: Optional[int] = None
    numero_parent: Optional[str] = None

#route pour modifier un eleve a partir de son id
@app.put("/modifierEleve/{eleve_id}")
def put_un_eleve(eleve_id: int, eleve: EleveModifier):
    conn = sqlite3.connect("ecole.db")
    cursor = conn.cursor()

    # Récupérer l'élève existant
    cursor.execute("SELECT * FROM eleve WHERE id=?", (eleve_id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = eleve.dict(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE eleve
        SET nom=?, prenom=?, sexe=?, date_naissance=?, lieu_naissance=?, adresse=?, nom_parent=?, redoublant=?, statut=?, classe_id=?, numero_parent=?
        WHERE id=?
    """
    valeurs = (
        donnees_actuelles["nom"],
        donnees_actuelles["prenom"],
        donnees_actuelles["sexe"],
        donnees_actuelles["date_naissance"],
        donnees_actuelles["lieu_naissance"],
        donnees_actuelles["adresse"],
        donnees_actuelles["nom_parent"],
        donnees_actuelles["redoublant"],
        donnees_actuelles["statut"],
        donnees_actuelles["classe_id"],
        donnees_actuelles["numero_parent"],
        eleve_id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "Élève modifié avec succès", "eleve": donnees_actuelles}

#route pour supprimer un eleve 
@app.delete("/supprimerEleve/{id}")
def delete_un_eleve(id: int = Path(ge=1)):
    conn = sqlite3.connect("ecole.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM eleve WHERE id = ?", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    conn.commit()
    conn.close()

    return {"message": "Élève supprimé avec succès"}

#route pour afficher le total des classes
@app.get("/total_classe")
def get_total_classe()-> dict:
    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM classe")
    total_classe = cursor.fetchone()[0]
    return {"total_classe": total_classe}

#affichage de la liste des classes
@app.get("/classe")
def get_all_classe()-> dict:
    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classe")
    classes = cursor.fetchall()
    return {"classes": classes}

#affichage d'une classe par son id
@app.get("/classe/{id}")
def get_classe_par_id(id: int = Path(ge=1))-> dict:

    conn = sqlite3.connect("ecole.db") 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classe WHERE id = ?", (id,))
    classe = cursor.fetchone()
    if classe is None:
        raise HTTPException(status_code=404, detail="classe non trouvée")
    return {"classe": classe}

# Modèle des données attendues dans le corps de la requête (JSON)
class classeAjouter(BaseModel):
    classe: str
    cycle_id: int

# 2. Route POST pour ajouter l'élève
@app.post("/classe")
def ajouter_classe(classe: classeAjouter):
    conn = sqlite3.connect("ecole.db")
    cursor = conn.cursor()

    sql = """
        INSERT INTO classe (
           classe, cycle_id
        ) VALUES (?, ?)
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

class classeModifier(BaseModel):
    classe: Optional[str] = None
    cycle_id: Optional[int] = None
   

#route pour modifier une classe a partir de son id
@app.put("/modifierClasse/{id}")
def put_un_eleve(id: int, classe: classeModifier):
    conn = sqlite3.connect("ecole.db")
    cursor = conn.cursor()

    # Récupérer l'élève existant
    cursor.execute("SELECT * FROM classe WHERE id=?", (id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="classe non trouvée")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = classe.dict(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE classe
        SET  classe=?, cycle_id=?
        WHERE id=?
    """
    valeurs = (
        donnees_actuelles["classe"],
        donnees_actuelles["cycle_id"],
        id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "classe modifiée avec succès", "classe": donnees_actuelles}

#route pour supprimer une classe
@app.delete("/supprimerClasse/{id}")
def delete_un_classe(id: int = Path(ge=1)):
    conn = sqlite3.connect("ecole.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM classe WHERE id = ?", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="classee non trouvée")

    conn.commit()
    conn.close()

    return {"message": "classe supprimée avec succès"}
