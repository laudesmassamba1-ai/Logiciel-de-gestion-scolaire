from fastapi import FastAPI
from pydantic import BaseModel

from database import (
    init_database,
    insert_cycles,
    insert_classes,
    insert_eleves
)


# ============================================================
# APPLICATION FASTAPI
# ============================================================

app = FastAPI(
    title="Gestion Scolaire API",
    version="1.0.0"
)


# ============================================================
# INITIALISATION DE LA BASE DE DONNÉES
# ============================================================

init_database()
insert_cycles()
insert_classes()
insert_eleves()


print("Base de données initialisée avec succès.")
print("Données des cycles chargées.")
print("Données des classes chargées.")
print("Données des élèves chargées.")


# ============================================================
# MODÈLE ÉLÈVE
# ============================================================

class Eleve(BaseModel):
    id: int
    nom: str
    prenom: str
    classe_id: int


# ============================================================
# MODÈLE D'UNE OPÉRATION DE SYNCHRONISATION
# ============================================================

class EleveSynchro(BaseModel):
    uuid_client: str
    eleve: Eleve


# ============================================================
# ROUTE PRINCIPALE
# ============================================================

@app.get("/")
def accueil():

    return {
        "message": "API Gestion Scolaire opérationnelle"
    }


# ============================================================
# ROUTE DE TEST
# ============================================================

@app.get("/test")
def test():

    return {
        "message": "Connexion FastAPI réussie"
    }


# ============================================================
# ROUTE PING
# ============================================================

@app.get("/ping")
def ping():

    return {
        "status": "online"
    }


# ============================================================
# AJOUTER UN ÉLÈVE
# ============================================================

@app.post("/eleves")
def ajouter_eleve(data: EleveSynchro):

    print("\n===================================")
    print("SYNCHRONISATION D'UN ÉLÈVE")
    print("===================================")

    print("UUID client :", data.uuid_client)
    print("Élève reçu :", data.eleve.model_dump())

    print("===================================\n")

    return {
        "message": "Élève synchronisé avec succès",
        "uuid_client": data.uuid_client,
        "eleve": data.eleve.model_dump()
    }