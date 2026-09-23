"""
Exercice fonctionnel de TOUTES les routes du serveur (mode SQLite).

Charge server/main.py comme `serveur_routes` (comme test_compat.py),
bascul le backend en SQLite sur un dossier temporaire puis pilote chaque
route avec des donnees reelles : un echec = 5xx ou exception TestClient
= regression bloquante pour le bureau comme pour le front web.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SERVER = Path(__file__).parent
sys.path.insert(0, str(_SERVER))


@pytest.fixture(scope="session")
def app_client(tmp_path_factory):
    import sqlite_backend
    os.environ["GS_DB_MODE"] = "sqlite"
    os.environ["GS_SQLITE_DIR"] = str(tmp_path_factory.mktemp("gs_routes"))
    os.environ["GS_JWT_SECRET"] = "x" * 40
    sqlite_backend._SCHEMA_APPLIQUE = False

    _spec = importlib.util.spec_from_file_location(
        "serveur_routes", _SERVER / "main.py")
    serveur = importlib.util.module_from_spec(_spec)
    sys.modules["serveur_routes"] = serveur
    _spec.loader.exec_module(serveur)

    return serveur, TestClient(serveur.app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def base(app_client):
    serveur, c = app_client

    def post(route, payload):
        r = c.post(route, json=payload)
        assert r.status_code < 500, f"{route} seed -> {r.status_code} {r.text}"
        return r

    cycle = post("/ajout_cycle", {"nom": "Primaire"}).json()["id"]
    classe = post("/ajout_classe", {"classe": "CP1", "cycle_id": cycle}).json()["id"]
    post("/ajouter_annee_scolaire",
         {"libelle": "2025-2026", "date_debut": "2025-09-01",
          "date_fin": "2026-06-30", "est_active": True})
    matiere = post("/ajout_matiere", {"nom": "Mathematiques"}).json()["id"]
    enseignant = post("/ajout_enseignant",
                      {"nom": "Kouassi", "prenom": "Jean", "sexe": "M",
                       "date_naissance": "1985-01-01",
                       "lieu_naissance": "Yamoussoukro", "adresse": "Rue 12",
                       "telephone": "0700000000", "email": "jean@ecole.ci",
                       "diplome": "Licence", "date_embauche": "2020-09-01",
                       "statut": "Enseignant"}).json()["id"]
    eleve = post("/ajout_eleve",
                 {"eleve": {"nom": "Bamba", "prenom": "Aya", "sexe": "F",
                            "date_naissance": "2015-05-10",
                            "lieu_naissance": "Abidjan", "adresse": "Cocody",
                            "nom_parent": "Bamba Mariam",
                            "telephone_parent": "0700000001", "redoublant": "0",
                            "statut": "Inscrit", "classe_id": classe},
                  "paiement": {"type_frais": "Inscription", "montant": 15000,
                               "mode_paiement": "Espèces"},
                  "uuid_client": "ue-1"}).json()["eleve_id"]
    return {"serveur": serveur, "c": c, "cycle": cycle, "classe": classe,
            "matiere": matiere, "enseignant": enseignant, "eleve": eleve}


GETS = [
    "/total_eleves", "/total_eleve_par_sexe", "/total_eleves_par_classe",
    "/total_eleve_par_classe", "/total_eleve_par_sexe_par_classe",
    "/eleve/CP1", "/eleve", "/eleve_recherche?nom=Bamba&prenom=Aya",
    "/eleve_total_classe?classe=CP1", "/eleve_supprime",
    "/parents_par_classe/CP1", "/total_classe", "/classe", "/classe/CP1",
    "/cycle", "/total_cycle", "/total_enseignant", "/enseignant",
    "/enseignant/Kouassi/Jean", "/total_paiement", "/total_montant_paiement",
    "/paiement", "/paiement/bilan/type_frais", "/paiement/bilan/2025-2026",
    "/paiement/bilan/trimestre/T1", "/paiement/bilan/eleve/Bamba/Aya",
    "/paiement/bilan/classe/CP1", "/paiement/bilan/mode_paiement/Espèces",
    "/paiement/bilan/mode_paiement/espece", "/paiement/eleve/Bamba/Aya",
    "/paiement/bilan/classe/total/CP1", "/total_note", "/note",
    "/note/eleve/Bamba/Aya", "/moyenne/Bamba/Aya/Composition",
    "/bulletin/Bamba/Aya/T1", "/total_presence/CP1", "/presence/CP1",
    "/liste_de_presence_par_classe/CP1", "/matiere", "/programme/CP1",
    "/lister_annees_scolaires", "/annee_scolaire_active", "/tarifs-scolarite",
    "/tarifs-scolarite/classe/1", "/inscriptions/1/solde",
    "/inscriptions/1/suivi-mensuel", "/utilisateurs", "/ping", "/audit",
    "/lister_toutes_les_inscriptions", "/toutes_presence", "/tous_les_programme",
    "/paiement-syndication", "/note-syndication", "/postes",
]


@pytest.fixture(scope="session")
def ecritures(app_client, base):
    """Toutes les ecritures du serveur (POST/PUT) avec des donnees valides."""
    c = app_client[1]

    def doit(methode, route, body):
            args = {"json": body} if body is not None else {}
            r = getattr(c, methode.lower())(route, **args)
            assert r.status_code < 500, f"{methode} {route} -> {r.status_code} {r.text}"
            return r

    doit("POST", "/ajout_cycle", {"nom": "College"})
    doit("POST", "/ajout_classe", {"classe": "CE1", "cycle_id": 1})
    doit("POST", "/ajouter_annee_scolaire",
         {"libelle": "2024-2025", "date_debut": "2024-09-01",
          "date_fin": "2025-06-30", "est_active": False})
    doit("POST", "/ajout_matiere", {"nom": "Francais"})
    doit("POST", "/ajout_enseignant",
         {"nom": "Nguessan", "prenom": "Sonia", "sexe": "F",
          "date_naissance": "1990-03-03", "lieu_naissance": "Daloa",
          "adresse": "Route 5", "telephone": "0700000004",
          "email": "sonia@ecole.ci", "diplome": "Master",
          "date_embauche": "2021-09-01", "statut": "Enseignant"})
    doit("POST", "/ajout_paiement",
         {"inscription_id": 1, "type_frais": "Scolarite", "montant": 50000,
          "mode_paiement": "Espèces", "trimestre": "T1", "mois": "Octobre"})
    for typ, note in (("Devoir 1", 14.0), ("Devoir 2", 12.0),
                      ("Composition", 16.0)):
        doit("POST", "/ajout_note",
             {"inscription_id": 1, "matiere_id": 1, "type_evaluation": typ,
              "note": note, "note_sur": 20, "date_evaluation": "2025-10-05",
              "trimestre": "T1"})
    doit("POST", "/ajout_presence",
         {"eleve_id": 1, "statut": "Present", "classe_id": 1, "justifie": "0"})
    doit("POST", "/associerMatiereClasseEnseignant",
         {"classe_id": 1, "matiere_id": 1, "enseignant_id": 1,
          "coefficient": 3})
    doit("POST", "/ajout_tarifs-scolarite",
         {"classe_id": 1, "frais_inscription": 15000, "montant_pension": 150000})
    doit("POST", "/ajout_tarifs-scolarite",
         {"classe_id": 2, "frais_inscription": 20000, "montant_pension": 160000})
    doit("POST", "/ajout_utilisateurs",
         {"nom": "Admin", "prenom": "Kilo", "telephone": "0700000099",
          "email": "admin@ecole.ci", "mot_de_passe": "motdepasseFort123",
          "role": "admin"})
    doit("POST", "/comptes",
         {"nom": "Secretaire", "email": "sec@ecole.ci",
          "telephone": "0700000005", "role": "gestionnaire"})
    for _ in range(2):
        doit("POST", "/parametre", {"cle": "ville", "valeur": "Abidjan"})
    doit("POST", "/eleve",
         {"eleve": {"nom": "Traore", "prenom": "Ibrahim", "sexe": "M",
                    "date_naissance": "2014-02-20", "lieu_naissance": "Bouake",
                    "adresse": "Zone 1", "nom_parent": "Traore Ali",
                    "numero_parent": "0700000003", "redoublant": 0,
                    "statut": "Inscrit", "classe_id": 1},
          "paiement": None, "uuid_client": "ue-2"})
    doit("POST", "/classe", {"classe": "CE1 B", "cycle_id": 1, "uuid_client": "cl-1"})
    doit("POST", "/cycle", {"nom": "Lycee"})
    doit("POST", "/matiere", {"nom": "Anglais"})
    doit("POST", "/enseignant",
         {"nom": "Toure", "prenom": "Aminata", "sexe": "F",
          "date_naissance": "1992-08-08", "lieu_naissance": "Korhogo",
          "adresse": "Sococo", "telephone": "0700000006", "email": "amina@ecole.ci",
          "diplome": "Licence", "date_embauche": "2022-09-01",
          "statut": "Professeur"})
    doit("POST", "/paiement",
         {"eleve_id": 2, "type_frais": "Scolarite", "montant": 20000,
          "mode_reglement": "espece", "trimestre": "T1", "mois": "Novembre"})
    doit("POST", "/tarifs-scolarite",
         {"classe_id": 1, "frais_inscription": 15000, "montant_pension": 150000})
    doit("POST", "/planning",
         {"classe_id": 1, "jour": "Lundi", "creneau": "08h-10h",
          "matiere": "Maths", "salle": "S1"})
    doit("PUT", "/modifierCycle/1", {"nom": "Primaire"})
    doit("PUT", "/classe/1", {"cycle_id": 1})
    doit("PUT", "/modifierEnseignant/1", {"telephone": "0700000002"})
    doit("PUT", "/eleve/1", {"statut": "Inscrit", "numero_parent": "0700000001"})
    doit("PUT", "/modifierPaiement/2", {"montant": 55000})
    doit("PUT", "/modifierPresence/1", {"statut": "Absent"})
    doit("PUT", "/annee_scolaire/1", {"libelle": "2025-2026"})
    doit("PUT", "/annee_scolaire/2/actif", {})
    doit("DELETE", "/planning/1", None)
    return app_client[1]


@pytest.mark.parametrize("route", GETS)
def test_route_sans_erreur(app_client, base, ecritures, route):
    c = app_client[1]
    r = c.get(route)
    assert r.status_code < 500, f"GET {route} -> {r.status_code} {r.text[:300]}"


def test_bulletin_calcule_la_moyenne(app_client, base, ecritures):
    c = app_client[1]
    r = c.get("/bulletin/Bamba/Aya/T1")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["eleve"]["nom"] == "Bamba"
    # moyenne = (moyenne_devoirs + 2 * moyenne_composition) / 3
    # devoirs: (14+12)/2 = 13 ; composition: 16 -> (13 + 32) / 3 = 15
    assert data["moyenne"] == pytest.approx(15.0, abs=0.01), data


def test_solde_eleve_coherent(app_client, base, ecritures):
    c = app_client[1]
    r = c.get("/inscriptions/1/solde")
    assert r.status_code == 200, r.text
    solde = r.json()
    assert solde["total_paye"] >= 15000, solde


def test_login_puis_audit_protege(app_client, base, ecritures):
    import hashlib
    server, c = app_client
    mdp = "motdepasseFort123"
    salt = "a" * 32
    h = hashlib.pbkdf2_hmac("sha256", mdp.encode(), bytes.fromhex(salt), 100000)
    hash_stocke = f"{salt}:{h.hex()}"
    conn = server.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO utilisateur (nom, prenom, telephone, email, identifiant, "
        "mot_de_passe, role, statut) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        ("Test", "Admin", "0700000098", "test.admin@ecole.ci", "testadmin",
         hash_stocke, "admin", "actif"))
    conn.commit()
    cur.close()
    conn.close()

    r = c.post("/login", json={"identifiant": "testadmin",
                               "mot_de_passe": mdp})
    assert r.status_code == 200, r.text
    token = r.json().get("token") or r.json().get("access_token")
    assert token
    assert c.get("/audit").status_code == 401
    assert c.get("/audit",
                 headers={"Authorization": "Bearer " + token}).status_code < 500


def test_ping_ok(app_client, base):
    assert app_client[1].get("/ping").status_code == 200


def test_presence_poste_enregistre_et_liste(app_client, base):
    serveur, c = app_client
    payload = {
        "uuid_poste": "test-poste-1",
        "nom_poste": "PC-Bureau",
        "adresse_ip": "192.168.1.12",
        "version_app": "1.6.0",
        "systeme": "Linux-6.8-test",
        "est_hote": True,
    }
    r = c.post("/present", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["uuid_poste"] == "test-poste-1"

    r = c.get("/postes")
    assert r.status_code == 200, r.text
    postes = r.json()["postes"]
    ligne = next((p for p in postes if p["uuid_poste"] == "test-poste-1"), None)
    assert ligne is not None, postes
    assert ligne["nom_poste"] == "PC-Bureau"
    assert ligne["est_hote"] == 1
    assert ligne["age_secondes"] is not None

    # Un second battement met a jour la fiche (pas de doublon).
    c.post("/present", json={**payload,
                             "nom_poste": "PC-Bureau (renomme)",
                             "est_hote": False})
    r = c.get("/postes")
    lignes = [p for p in r.json()["postes"] if p["uuid_poste"] == "test-poste-1"]
    assert len(lignes) == 1, lignes
    assert lignes[0]["nom_poste"] == "PC-Bureau (renomme)"
    assert lignes[0]["est_hote"] == 0

    # uuid vide = refus.
    assert c.post("/present", json={**payload, "uuid_poste": ""}).status_code == 400