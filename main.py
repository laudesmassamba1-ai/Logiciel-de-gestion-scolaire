from fastapi import FastAPI, Path, HTTPException
from pydantic import BaseModel
from typing import Optional
from typing import Optional
import mysql.connector

app = FastAPI()
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Josias50",
        database="ecole"
    )

#affichage du nombre total d'élèves
@app.get("/total_eleves")
def get_total_eleves()-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM eleve")
    total_eleves = cursor.fetchone()[0]
    return {"total_eleves": total_eleves}

#affichage du nombre total d'élèves par classe
@app.get("/total_eleves_par_classe")
def get_total_eleves_par_classe(recherche: Optional[str]=None)-> dict:
    conn = get_connection()
    cursor = conn.cursor()
    if recherche:
        sql="""SELECT COUNT(*) FROM eleve, classe WHERE eleve.classe_id=classe.id AND classe like %s"""
        motif=f"%{recherche}%"
        cursor.execute(sql, (motif,))
        total_eleves = cursor.fetchone()[0]
        cursor.execute("SELECT classe FROM classe where classe like %s", (motif,))
    classe = cursor.fetchone()[0]
    return {"nombre total d'élèves": {classe: total_eleves}}

#affichage de la liste des élèves par classe
@app.get("/eleve/{classe_id}")
def get_all_eleves_par_classe(classe_id: int = Path(ge=1))-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT eleve.id, nom, prenom, sexe, classe FROM eleve, classe where eleve.classe_id=classe.id and classe.id = %s",(classe_id, ))
    eleves = cursor.fetchall()
    return {"eleves": eleves}

#afficher la liste des eleves par classe
@app.get("/eleve/{classe_id}")
def get_eleve_par_classe(classe_id: int = Path(ge=1))-> dict:
    conn = get_connection()
    cursor=conn.cursor(dictionary=True)
    cursor.execute("select nom, prenom, sexe, classe from eleve, classe where eleve.classe_id =classe.id and eleve.classe_id= %s", (classe_id,))
    classe= cursor.fetchall()
    if classe is None:
        raise HTTPException(status_code=404, detail="classe non trouvee")
    return{"liste eleve par classe": classe}

#affichage d'un élève par son nom
@app.get("/eleve_recherche")
def get_eleve_par_son_nom(recherche: Optional[str]=None, recherche1: Optional[str]=None)-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if recherche:
        sql="""select eleve.id, nom, prenom, sexe, date_naissance, lieu_naissance, adresse, nom_parent, redoublant, statut, numero_parent, classe from eleve, classe where eleve.classe_id=classe.id and nom like  %s and prenom like %s"""
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

# Modèle des données attendues dans le corps de la requête (JSON)
class Eleveajouter(BaseModel):
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

# Modèle des données attendues dans le corps de la requête (JSON)
#pour gerer les inscriptions en debut d'annee
class paiementAjouter(BaseModel):
    eleve_id: Optional[int]= None
    type_frais: str
    montant: float
    date_paiement: str
    mode_paiement: str
    annee_scolaire: str
    trimestre: str

# 2. Route POST pour ajouter l'élève
@app.post("/eleve")
def ajouter_eleve(eleve: Eleveajouter, paiement: paiementAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        sql = """
            INSERT INTO eleve (
            nom, prenom, sexe, date_naissance,
            lieu_naissance, adresse, nom_parent,
            redoublant, statut, classe_id, numero_parent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """

        valeurs = (
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

        nouvel_id = cursor.lastrowid

        sql_paiement = """insert into paiement (eleve_id, type_frais, montant, date_paiement, mode_paiement, annee_scolaire, trimestre) values ( %s, %s, %s, %s, %s, %s, %s)"""

        valeurs_paiement = (
            nouvel_id,
            paiement.type_frais,
            paiement.montant,
            paiement.date_paiement,
            paiement.mode_paiement,
            paiement.annee_scolaire,
            paiement.trimestre
        )
        cursor.execute(sql_paiement, valeurs_paiement)
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'ajout de l'élève et du paiement: {str(e)}")
    finally:
        conn.close()

    return {
            "message": "Élève ajouté avec succès",
            "id": nouvel_id,
            "eleve": eleve.dict()
        }

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
    classe_id: Optional[int] = None
    numero_parent: Optional[str] = None

## Route pour modifier un élève à partir de son id
@app.put("/modifierEleve/{id}")
def put_un_eleve(id: int, eleve: EleveModifier):
    #Extraire uniquement les champs envoyés
    nouvelles_donnees = eleve.dict(exclude_unset=True)

    if not nouvelles_donnees:
        raise HTTPException(status_code=400, detail="Aucun champ à modifier n'a été fourni")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Vérifier si l'élève existe
    cursor.execute("SELECT id FROM eleve WHERE id=%s", (id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    #Construire et exécuter la mise à jour dynamique
    clauses_set = [f"{cle}=%s" for cle in nouvelles_donnees.keys()]
    sql = f"UPDATE eleve SET {', '.join(clauses_set)} WHERE id=%s"

    valeurs = list(nouvelles_donnees.values())
    valeurs.append(id)

    cursor.execute(sql, tuple(valeurs))
    conn.commit()

    #Récupérer la fiche COMPLÈTE et À JOUR de l'élève
    cursor.execute("SELECT * FROM eleve WHERE id=%s", (id,))
    eleve_mis_a_jour = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "message": "Élève modifié avec succès",
        "eleve": eleve_mis_a_jour
    }

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
    cursor.execute("SELECT * FROM eleve WHERE est_supprime = TRUE")
    eleves_supprimes = cursor.fetchall()
    return {"eleves_supprimes": eleves_supprimes}

#route pour restaurer un élève supprimé/archivé
@app.put("/restaurer_eleve/{nom}")
def restaurer_eleve(nom: str):
    conn = get_connection()
    cursor = conn.cursor()

    # On restaure l'élève en le démarquant comme non-supprimé
    cursor.execute("UPDATE eleve SET est_supprime = FALSE WHERE nom = %s", (nom,))
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
        SELECT nom, prenom, nom_parent, numero_parent, classe FROM eleve, classe 
        WHERE eleve.classe_id = classe.id AND classe.classe LIKE %s
    """, (f"{classe_name}",))
    parents = cursor.fetchall()
    return {"parents": parents}

#route pour afficher le total des classes
@app.get("/total_classe")
def get_total_classe()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) FROM classe")
    total_classe = cursor.fetchone()[0]
    return {"total_classe": total_classe}

#affichage de la liste des classes
@app.get("/classe")
def get_all_classe()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM classe")
    classes = cursor.fetchall()
    return {"classes": classes}

#affichage d'une classe par son id
@app.get("/classe/{id}")
def get_classe_par_id(id: int = Path(ge=1))-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM classe WHERE id = %s", (id,))
    classe = cursor.fetchone()
    if classe is None:
        raise HTTPException(status_code=404, detail="classe non trouvée")
    return {"classe": classe}

# Modèle des données attendues dans le corps de la requête (JSON)
class classeAjouter(BaseModel):
    classe: str
    cycle_id: int

# 2. Route POST pour ajouter une classe
@app.post("/classe")
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

class classeModifier(BaseModel):
    classe: Optional[str] = None
    cycle_id: Optional[int] = None
   

#route pour modifier une classe a partir de son id
@app.put("/modifierClasse/{id}")
def put_une_classe(id: int, classe: classeModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer une classe existante
    cursor.execute("SELECT * FROM classe WHERE id=%s", (id,))
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
        SET  classe=%s, cycle_id=%s
        WHERE id=%s
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
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM classe WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="classee non trouvée")

    conn.commit()
    conn.close()

    return {"message": "classe supprimée avec succès"}

#route pour afficher le total des cycles
@app.get("/total_cycle")
def get_total_cycle()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
@app.post("/cycle")
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

class cycleModifier(BaseModel):
    nom: Optional[str] = None
   
   

#route pour modifier un cycle a partir de son id
@app.put("/modifierCycle/{id}")
def put_un_cycle(id: int, cycle: cycleModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer un cycle existant
    cursor.execute("SELECT * FROM cycle WHERE id=%s", (id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="cycle non trouvé")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = cycle.dict(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE cycle
        SET  nom=%s
        WHERE id=%s
    """
    valeurs = (
        donnees_actuelles["nom"],
        id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "cycle modifié avec succès", "cycle": donnees_actuelles}

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
    cursor = conn.cursor(dictionary=True)
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
@app.get("/enseignant/{id}")
def get_enseignant_par_id(id: int = Path(ge=1))-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM enseignant WHERE id = %s", (id,))
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
    matiere_principale: str
    diplome: str
    date_embauche: str
    statut: str
   

# 2. Route POST pour ajouter l'élève
@app.post("/enseignant")
def ajouter_enseignant(enseignant: enseignantAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO enseignant (
         nom, prenom, sexe, date_naissance, lieu_naissance, adresse, telephone, email, matiere_principale, diplome, date_embauche, statut
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
      enseignant.matiere_principale,
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
    matiere_principale: Optional[str] = None
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
@app.delete("/supprimerEnseignant/{id}")
def delete_un_enseignant(id: int = Path(ge=1)):
    conn=get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM enseignant WHERE id = %s", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="enseignant non trouvé")

    conn.commit()
    conn.close()

    return {"message": "enseignant supprimé avec succès"}

#route pour afficher le total de paiements
@app.get("/total_paiement")
def get_total_paiement()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) FROM paiement")
    total_paiement = cursor.fetchone()[0]
    return {"total_paiement": total_paiement}

#affichage de la liste des paiements
@app.get("/paiement")
def get_all_paiement()-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM paiement")
    paiement = cursor.fetchall()
    return {"paiement": paiement}

#affichage d'un paiement par son id
@app.get("/paiement/{id}")
def get_paiement_par_id(id: int = Path(ge=1))-> dict:

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM paiement WHERE id = %s", (id,))
    paiement = cursor.fetchone()
    if paiement is None:
        raise HTTPException(status_code=404, detail="paiement non trouvé")
    return {"paiement": paiement}


# 2. Route POST pour ajouter un paiement
@app.post("/paiement")
def ajouter_paiement(paiement: paiementAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO paiement (
            eleve_id, type_frais, montant, date_paiement, mode_paiement, annee_scolaire, trimestre
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    valeurs = (
        paiement.eleve_id,
        paiement.type_frais,
        paiement.montant,
        paiement.date_paiement,
        paiement.mode_paiement,
        paiement.annee_scolaire,
        paiement.trimestre
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
    eleve_id: Optional[int] = None
    type_frais: Optional[str] = None
    montant: Optional[float] = None
    date_paiement: Optional[str] = None
    mode_paiement: Optional[str] = None
    annee_scolaire: Optional[str] = None
    trimestre: Optional[str] = None

#route pour modifier un paiement a partir de son id
@app.put("/modifierPaiement/{id}")
def put_un_paiement(id: int, paiement: paiementModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer un paiement existant
    cursor.execute("SELECT * FROM paiement WHERE id=%s", (id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="paiement non trouvé")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = paiement.dict(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE paiement
        SET  eleve_id=%s, type_frais=%s, montant=%s, date_paiement=%s, mode_paiement=%s, annee_scolaire=%s, trimestre=%s
        WHERE id=%s
    """
    valeurs = (
        donnees_actuelles["eleve_id"],
        donnees_actuelles["type_frais"],
        donnees_actuelles["montant"],
        donnees_actuelles["date_paiement"],
        donnees_actuelles["mode_paiement"],
        donnees_actuelles["annee_scolaire"],
        donnees_actuelles["trimestre"],
        id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "paiement modifié avec succès", "paiement": donnees_actuelles}

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
    cursor = conn.cursor(dictionary=True)
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

#affichage d'une note par son id
@app.get("/note/{id}")
def get_note_par_id(id: int = Path(ge=1))-> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM note WHERE id = %s", (id,))
    note = cursor.fetchone()
    if note is None:
        raise HTTPException(status_code=404, detail="note non trouvée")
    return {"note": note}

# Modèle des données attendues dans le corps de la requête (JSON)
class noteAjouter(BaseModel):
    eleve_id: int
    enseignant_id: int
    matiere: str
    type_evaluation: str
    note: float
    note_sur: int
    coefficient: int
    date_evaluation: str
    trimestre: str
    annee_scolaire: str

# 2. Route POST pour ajouter une note
@app.post("/note")
def ajouter_note(note: noteAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        INSERT INTO note (
            eleve_id, enseignant_id, matiere, type_evaluation, note, note_sur, coefficient, date_evaluation, trimestre, annee_scolaire
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    valeurs = (
        note.eleve_id,
        note.enseignant_id,
        note.matiere,
        note.type_evaluation,
        note.note,
        note.note_sur,
        note.coefficient,
        note.date_evaluation,
        note.trimestre,
        note.annee_scolaire
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
    eleve_id: Optional[int] = None
    enseignant_id: Optional[int] = None
    matiere: Optional[str] = None
    type_evaluation: Optional[str] = None
    note: Optional[float] = None
    note_sur: Optional[int] = None
    coefficient: Optional[int] = None
    date_evaluation: Optional[str] = None
    trimestre: Optional[str] = None
    annee_scolaire: Optional[str] = None

#route pour modifier une note a partir de son id
@app.put("/modifierNote/{id}")
def put_un_note(id: int, note: noteModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer une note existante
    cursor.execute("SELECT * FROM note WHERE id=%s", (id,))
    existant = cursor.fetchone()
    if existant is None:
        conn.close()
        raise HTTPException(status_code=404, detail="note non trouvée")

    colonnes = [d[0] for d in cursor.description]
    donnees_actuelles = dict(zip(colonnes, existant))

    # Fusionner : on garde l'ancienne valeur si rien n'a été envoyé
    nouvelles_donnees = note.dict(exclude_unset=True)
    donnees_actuelles.update(nouvelles_donnees)

    # Mettre à jour avec les valeurs fusionnées
    sql = """
        UPDATE note
        SET  eleve_id=%s, enseignant_id=%s, matiere=%s, type_evaluation=%s, note=%s, note_sur=%s, coefficient=%s, date_evaluation=%s, trimestre=%s, annee_scolaire=%s
        WHERE id=%s
    """
    valeurs = (
        donnees_actuelles["eleve_id"],
        donnees_actuelles["enseignant_id"],
        donnees_actuelles["matiere"],
        donnees_actuelles["type_evaluation"],
        donnees_actuelles["note"],
        donnees_actuelles["note_sur"],
        donnees_actuelles["coefficient"],
        donnees_actuelles["date_evaluation"],
        donnees_actuelles["trimestre"],
        donnees_actuelles["annee_scolaire"],
        id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "note modifiée avec succès", "note": donnees_actuelles}

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

#route pour calculer la moyenne d'un élève par son id et l'afficher avec les informations de l'élève
@app.get("/moyenne/{eleve_id}")
def get_moyenne(eleve_id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor()

    #Vérifier que l'élève existe, et le récupérer proprement
    cursor.execute("SELECT * FROM eleve WHERE id = %s", (eleve_id,))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    colonnes = [d[0] for d in cursor.description]
    eleve = dict(zip(colonnes, ligne))

    #Moyenne pondérée par les coefficients
    cursor.execute("""
        SELECT SUM(note * coefficient) / SUM(coefficient)
        FROM note
        WHERE eleve_id = %s
    """, (eleve_id,))
    resultat = cursor.fetchone()
    moyenne = resultat[0] if resultat else None

    conn.close()

    return {
        "eleve": eleve,
        "moyenne": round(moyenne, 2) if moyenne is not None else None
    }

#route pour afficher le total des presences par classe
@app.get("/total_presence/{classe_id}")
def get_total_presence(classe_id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    #Vérifier que la classe existe
    cursor.execute("SELECT * FROM classe WHERE id = %s", (classe_id,))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Classe non trouvée")

    #Compter le nombre de présences pour cette classe
    cursor.execute("""
        SELECT COUNT(*)
        FROM presences
        WHERE classe_id = %s
    """, (classe_id,))
    total_presence = cursor.fetchone()[0]

    conn.close()

    return {
        "classe_id": classe_id,
        "total_presence": total_presence
    }

#route pour afficher la liste des presences par classe
@app.get("/presence/{classe_id}")
def get_presence_par_classe(classe_id: int = Path(ge=1)):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    #Vérifier que la classe existe
    cursor.execute("SELECT * FROM classe WHERE id = %s", (classe_id,))
    ligne = cursor.fetchone()
    if ligne is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Classe non trouvée")

    #Récupérer la liste des présences pour cette classe
    cursor.execute("""
        SELECT *
        FROM presences
        WHERE classe_id = %s
    """, (classe_id,))
    presence = cursor.fetchall()

    conn.close()

    return {
        "classe_id": classe_id,
        "presence": presence
    }

#route pour ajouter une présence pour un élève dans une classe
class PresenceAjouter(BaseModel):
    eleve_id: int
    date_presence: str
    statut: str  
    justifie: Optional[str] = None
    commentaire: Optional[str] = None
    classe_id: int

@app.post("/presence")
def ajouter_presence(presence: PresenceAjouter):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Vérifier que l'élève existe
    cursor.execute("SELECT * FROM eleve WHERE id = %s", (presence.eleve_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Élève non trouvé")

    sql = """
        INSERT INTO presences (eleve_id, date_presence, statut, justifie, commentaire, classe_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    valeurs = (
        presence.eleve_id,
        presence.date_presence,
        presence.statut,
        presence.justifie,
        presence.commentaire,
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
    date_presence: Optional[str] = None
    statut: Optional[str] = None  
    justifie: Optional[str] = None
    commentaire: Optional[str] = None
    classe_id: Optional[int] = None

#route pour modifier une présence pour un élève dans une classe
@app.put("/modifierPresence/{presence_id}")
def modifier_presence(presence_id: int, presence: PresenceModifier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Récupérer la présence existante
    cursor.execute("SELECT * FROM presences WHERE id=%s", (presence_id,))
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
        SET eleve_id=%s, date_presence=%s, statut=%s, justifie=%s, commentaire=%s, classe_id=%s
        WHERE id=%s
    """
    valeurs = (
        donnees_actuelles["eleve_id"],
        donnees_actuelles["date_presence"],
        donnees_actuelles["statut"],
        donnees_actuelles["justifie"],
        donnees_actuelles["commentaire"],
        donnees_actuelles["classe_id"],
        presence_id,
    )
    cursor.execute(sql, valeurs)
    conn.commit()
    conn.close()

    return {"message": "Présence modifiée avec succès", "presence": donnees_actuelles}

#route pour supprimer une présence pour un élève dans une classe
@app.delete("/supprimerPresence/{presence_id}")
def supprimer_presence(presence_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM presences WHERE id = %s", (presence_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Présence non trouvée")

    conn.commit()
    conn.close()

    return {"message": "Présence supprimée avec succès"}