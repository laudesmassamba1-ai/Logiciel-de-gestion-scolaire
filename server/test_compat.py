"""
Tests d'integration de la couche de compatibilite serveur (compat.py).

Ces tests utilisent TestClient de FastAPI avec une fausse connexion MySQL :
ils valident le routage, la normalisation des payloads de l'application
de bureau et la forme des reponses, sans base de donnees reelle.

Execution :
    pip install fastapi pydantic mysql-connector-python bcrypt httpx2
    python -m pytest test_compat.py -v
"""

import sys
import warnings
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
warnings.filterwarnings("ignore")

# Le bureau a aussi un main.py : selon l'ordre des suites dans une meme
# session pytest, "import main" peut resoudre vers le MAUVAIS module.
# On charge donc explicitement le main du SERVEUR sous un nom dedie.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "serveur_main", Path(__file__).parent / "main.py")
serveur_main = importlib.util.module_from_spec(_spec)
sys.modules["serveur_main"] = serveur_main
_spec.loader.exec_module(serveur_main)

import pytest
from fastapi.testclient import TestClient

import compat


# ============================================================
# FAUSSE BASE MYSQL
# ============================================================

REPONSES = [
    ("select id from eleve where id", [(7,)]),
    ("select * from eleve where id", [(7, "MBEMBA")]),
    ("select id from inscription where eleve_id", [(11,)]),
    ("select id from annee_scolaire where id", [(2,)]),
    ("select id from annee_scolaire where est_active", [(2,)]),
    ("select id from classe where id", [(3,)]),
    ("select id from enseignant where id", [(4,)]),
    ("select * from enseignant where id",
     [(4, "Jean", "LOKO")]),
    # Repli general : les COUNT(*) renvoient toujours une ligne en MySQL reel
    ("select count(*)", [(0,)]),
]


class FauxCurseur:

    def __init__(self):
        self.execution = None
        self.params = None
        self._lignes = []
        self.rowcount = 1
        self.description = None
        self.lastrowid = 42
        self.historique = []

    def execute(self, sql, params=None):
        self.execution = sql.strip()
        self.params = params or ()
        self.historique.append((sql.strip(), params))
        cle = sql.strip().lower()
        for motif, lignes in REPONSES:
            if motif in cle:
                self._lignes = list(lignes)
                return
        self._lignes = []

    def fetchone(self):
        return self._lignes[0] if self._lignes else None

    def fetchall(self):
        return self._lignes

    def close(self):
        pass


class FauxConnexion:

    def __init__(self):
        self.curseur_obj = FauxCurseur()

    def cursor(self, *args, **kwargs):
        return self.curseur_obj

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture()
def client(tmp_path):
    fausse_conn = FauxConnexion()
    with patch.object(compat, "connexion", return_value=fausse_conn):
        with patch.object(serveur_main, "get_connection", return_value=fausse_conn):
            yield TestClient(serveur_main.app), fausse_conn


def dernier_update(conn, prefixe):
    maj = [s for s, _ in conn.curseur_obj.historique if s.startswith(prefixe)]
    assert maj, f"aucun {prefixe} execute"
    return maj[-1]


def dernier_sql(conn, fragment):
    """Dernier SQL execute contenant `fragment` (les lectures serveur
    n'ecrivent rien : seule l'historique du faux curseur permet de les
    controler)."""
    sqls = [s for s, _ in conn.curseur_obj.historique if fragment in s]
    assert sqls, f"aucune requete contenant « {fragment} »"
    return sqls[-1]


# ============================================================
# NORMALISATEURS PURS
# ============================================================

def test_normalisation_sexe():
    assert compat._sexe("femme") == "F"
    assert compat._sexe("M") == "M"
    assert compat._sexe(None) == "M"


def test_normalisation_redoublant():
    assert compat._redoublant(True) == "1"
    assert compat._redoublant(0) == "0"
    assert compat._redoublant("oui") == "1"
    assert compat._redoublant("n'importe") == "0"


def test_normalisation_statut_eleve():
    assert compat._statut_eleve("Inscrit") == "actif"
    assert compat._statut_eleve("radié") == "exclu"
    assert compat._statut_eleve("Exclu") == "exclu"
    assert compat._statut_eleve("inconnu") == "actif"


def test_normalisation_eleve_bureau_vers_serveur():
    bureau = {
        "matricule": "ELEV20260001", "nom": "MBEMBA", "prenom": "Jean",
        "sexe": "M", "date_naissance": "2015-03-04",
        "lieu_naissance": "Brazzaville", "adresse": "Talangai",
        "pere_nom": "Paul MBEMBA", "pere_tel": "+242066123456",
        "mere_nom": "Marie", "mere_tel": "0607",
        "redoublant": 0, "check_acte": 0, "statut": "Inscrit",
        "classe_id": 3, "uuid_client": "abc-123",
    }
    n = compat._normaliser_eleve(bureau)
    assert n["nom_parent"] == "Paul MBEMBA"
    assert n["numero_parent"] == "+242066123456"
    assert n["statut"] == "actif"
    assert n["redoublant"] == "0"
    assert "matricule" not in n and "check_acte" not in n


def test_normalisation_trimestre():
    cas = [("T1", "T1"), ("t2", "T2"), ("1er Trimestre", "T1"),
           ("Trim 2", "T2"), ("3ème trimestre", "T3"),
           ("", None), (None, None), ("Semestre 1", None)]
    for brut, attendu in cas:
        assert compat._trimestre(brut) == attendu, brut


def test_normalisation_type_frais_et_mode():
    assert compat._type_frais("Scolarité") == "Scolarite"
    assert compat._type_frais("Inscription") == "Inscription"
    assert compat._type_frais("Tenue scolaire") == "Scolarite"  # ENUM-safe
    assert compat._mode_paiement("Espèces") == "espece"
    assert compat._mode_paiement("Mobile Money") == "mobile_money"
    assert compat._mode_paiement("Chèque") == "cheque"
    assert compat._mode_paiement(None) == "espece"


def test_normalisation_presence_et_dates():
    assert compat._statut_presence("Retard") == "En retard"
    assert compat._statut_presence("Absent") == "Absent"
    assert compat._date_sql("04/03/2015") == "2015-03-04"
    assert compat._date_sql("") is None
    assert compat._date_sql("n'importe quoi") is None


def test_decoupage_nom_complet():
    assert compat._decouper_nom_complet({"nom_complet": "Jean MBEMBA"}) == ("Jean", "MBEMBA")
    assert compat._decouper_nom_complet({"nom_complet": "Madilu"}) == ("Madilu", "-")
    assert compat._decouper_nom_complet({"nom": "Diallo", "prenom": "Awa"}) == ("Diallo", "Awa")


def test_id_entier_securise():
    assert compat._id_entier("12") == 12
    assert compat._id_entier(None) is None
    assert compat._id_entier("abc") is None


# ============================================================
# ELEVES
# ============================================================

def test_post_eleve_forme_plate_bureau(client):
    c, _ = client
    r = c.post("/eleve", json={
        "nom": "MBEMBA", "prenom": "Jean", "sexe": "M",
        "date_naissance": "2015-03-04", "lieu_naissance": "Brazzaville",
        "adresse": "Talangai", "pere_nom": "Paul", "pere_tel": "066123456",
        "statut": "Inscrit", "classe_id": 3, "uuid_client": "u-1"})
    assert r.status_code == 200, r.text
    assert r.json()["eleve_id"] == 42


def test_post_eleve_forme_enveloppee_avec_paiement(client):
    c, conn = client
    r = c.post("/eleve", json={"uuid_client": "u-9",
                               "eleve": {"nom": "A", "prenom": "B", "sexe": "F",
                                         "classe_id": 2},
                               "paiement": {"type_frais": "Inscription",
                                            "montant": 15000,
                                            "mode_paiement": "Espèces"}})
    assert r.status_code == 200, r.text
    insertions_paiement = [s for s, _ in conn.curseur_obj.historique
                           if "INSERT INTO paiement" in s]
    assert insertions_paiement


def test_post_eleve_sans_classe_refuse_400(client):
    """C2 : un eleve cree sans classe est invisible de toutes les routes de
    lecture (jointures inscription/classe). Le serveur refuse donc la creation
    : le poste garde l'operation en file et la rejouera apres resolution."""
    c, conn = client
    r = c.post("/eleve", json={
        "nom": "ORPHELIN", "prenom": "Ali", "sexe": "M",
        "statut": "Inscrit", "uuid_client": "u-orphan"})
    assert r.status_code == 400, r.text
    assert "Classe non renseignee" in r.json()["detail"]
    insertions_eleve = [s for s, _ in conn.curseur_obj.historique
                        if "INSERT INTO eleve" in s]
    assert not insertions_eleve


def test_lectures_eleve_ignorent_les_archives(client):
    """Tombstone : un eleve archive (est_supprime) ne doit plus ressortir
    dans la recherche, les parents par classe ni la syndication (sinon la
    sync resolvait son id et pouvait le modifier / le payer)."""
    c, conn = client
    r = c.get("/eleve_recherche", params={"recherche": "Kone"})
    assert r.status_code == 200, r.text
    sql_recherche = dernier_sql(conn, "from eleve, inscription, classe")
    assert "est_supprime = 0" in sql_recherche
    assert "LOWER(eleve.nom)" in sql_recherche

    c.get("/parents_par_classe/CP1")
    sql_parents = dernier_sql(conn, "FROM eleve, classe, inscription")
    assert "est_supprime = 0" in sql_parents

    c.get("/eleve-syndication")
    sql_syndication = dernier_sql(conn, "SELECT id, uuid_client FROM eleve")
    assert "est_supprime = 0" in sql_syndication


def test_put_modifier_eleve_champs_bureau_uniquement(client):
    c, conn = client
    r = c.put("/modifierEleve/5", json={"pere_nom": "Nouveau pere",
                                        "mere_tel": "06"})
    assert r.status_code == 200, r.text
    maj = dernier_update(conn, "UPDATE eleve")
    assert "nom_parent" in maj and "numero_parent" in maj


def test_suppression_cascade_donnees_eleve(client):
    c, _ = client
    for suffixe in ("notes", "presences", "paiements"):
        r = c.delete(f"/eleve/5/{suffixe}")
        assert r.status_code == 200, r.text


# ============================================================
# CLASSES / CYCLES / MATIERES / PROGRAMMES
# ============================================================

def test_supprimer_classe_par_id_et_par_nom(client):
    c, _ = client
    assert c.delete("/supprimerClasse/3").status_code == 200
    assert c.delete("/supprimerClasse/inconnue").status_code == 404


def test_supprimer_classe_archive_eleves_avant_les_inscriptions(client):
    """Regression C1 : l'UPDATE est_supprime doit precéder le DELETE des
    inscriptions, sinon les eleves de la classe restent actifs sans
    inscription et deviennent invisibles sur tous les postes."""
    c, conn = client
    conn.curseur_obj.historique = []
    assert c.delete("/supprimerClasse/3").status_code == 200
    ordre = [sql.strip().lower() for sql, _ in conn.curseur_obj.historique]
    i_update = next(i for i, s in enumerate(ordre)
                    if s.startswith("update eleve set est_supprime"))
    i_delete = next(i for i, s in enumerate(ordre)
                    if s.startswith("delete from inscription"))
    assert i_update < i_delete


def test_classe_cycle_validation(client):
    c, _ = client
    assert c.post("/classe", json={"nom": "Terminale C", "cycle_id": 1}).status_code == 200
    assert c.put("/modifierClasse/3", json={"nom": "Terminale D"}).status_code == 200
    assert c.post("/classe", json={"nom": "Sans cycle"}).status_code == 400
    assert c.post("/cycle", json={"nom": "Lycee", "description": "x"}).status_code == 200


def test_matieres_et_programmes(client):
    c, _ = client
    assert c.post("/matiere", json={"nom": "Maths", "coefficient": 4}).status_code == 200
    assert c.put("/modifierMatiere/1", json={"nom": "Maths", "coefficient": 3}).status_code == 200
    assert c.delete("/supprimerMatiere/1").status_code == 200
    assert c.post("/associerMatiereClasseEnseignant",
                  json={"classe_id": 1, "matiere_id": 1, "enseignant_id": 1,
                        "coefficient": 2}).status_code == 200
    assert c.delete("/supprimerProgramme/1").status_code == 200


# ============================================================
# ENSEIGNANTS
# ============================================================

def test_post_enseignant_decoupe_nom_complet(client):
    c, conn = client
    r = c.post("/enseignant", json={"nom_complet": "Jean LOKO", "fonction": "Prof",
                                    "telephone": "066111222", "email": "j@l.cg",
                                    "salaire": 250000, "statut": "actif"})
    assert r.status_code == 200, r.text
    insertion = [p for s, p in conn.curseur_obj.historique
                 if s.startswith("INSERT INTO enseignant")][-1]
    assert insertion[0] == "Jean" and insertion[1] == "LOKO"


def test_get_enseignant_par_id(client):
    c, _ = client
    r = c.get("/enseignant/4")
    assert r.status_code == 200 and "enseignant" in r.json()


def test_put_modifier_enseignant_nom_complet(client):
    c, conn = client
    r = c.put("/modifierEnseignant/4", json={"nom_complet": "Awa Diallo"})
    assert r.status_code == 200, r.text
    maj = dernier_update(conn, "UPDATE enseignant")
    assert "nom = %s" in maj and "prenom = %s" in maj


def test_delete_enseignant_par_id(client):
    c, _ = client
    assert c.delete("/supprimerEnseignant/4").status_code == 200


# ============================================================
# FINANCE
# ============================================================

def test_post_tarif_forme_bureau_inscription(client):
    c, conn = client
    r = c.post("/tarifs-scolarite",
               json={"classe_id": 3, "type_frais": "Inscription",
                     "montant": 15000, "annee_scolaire": "2025-2026"})
    assert r.status_code == 200, r.text
    insertion = [p for s, p in conn.curseur_obj.historique
                 if "INSERT INTO tarif_scolarite" in s][-1]
    assert float(insertion[2]) == 15000.0 and float(insertion[3]) == 0.0


def test_put_tarif_forme_bureau(client):
    c, _ = client
    r = c.put("/tarifs-scolarite/7",
              json={"montant": 180000, "type_frais": "Scolarite"})
    assert r.status_code == 200, r.text


def test_post_paiement_dispatch_caisse_vs_eleve(client):
    c, conn = client
    avant = len(conn.curseur_obj.historique)
    r = c.post("/paiement", json={"reference": "REC-AB12", "beneficiaire": "X",
                                  "motif": "Craie", "categorie": "Fournitures",
                                  "montant": 5000, "type": "sortie"})
    assert r.status_code == 200, r.text
    assert any("caisse_transaction" in s
               for s, _ in conn.curseur_obj.historique[avant:])

    avant = len(conn.curseur_obj.historique)
    r = c.post("/paiement", json={"eleve_id": 7, "montant": 25000,
                                  "mode_reglement": "Mobile Money",
                                  "type_frais": "Scolarite", "trimestre": "T1"})
    assert r.status_code == 200, r.text
    insertion = [p for s, p in conn.curseur_obj.historique[avant:]
                 if s.startswith("INSERT INTO paiement")][-1]
    # (inscription_id, type_frais, montant, mode_paiement, trimestre, mois, uuid_client)
    assert insertion[3] == "mobile_money" and insertion[4] == "T1"


# ============================================================
# NOTES / PRESENCES
# ============================================================

def test_post_note_multi_composantes(client):
    c, conn = client
    avant = len([s for s, _ in conn.curseur_obj.historique
                 if "INSERT INTO note" in s])
    r = c.post("/note", json={"eleve_id": 7, "matiere_id": 2, "periode": "Trim 2",
                              "devoir1": 12, "composition": 14.5})
    assert r.status_code == 200, r.text
    nb = len([s for s, _ in conn.curseur_obj.historique
              if "INSERT INTO note" in s]) - avant
    assert nb == 2, nb


def test_post_presence_mapping_retard(client):
    c, conn = client
    r = c.post("/presence", json={"eleve_id": 7, "classe_id": 3,
                                  "date": "2026-08-24", "statut": "Retard",
                                  "motif": "Embouteillage"})
    assert r.status_code == 200, r.text
    insertion = [p for s, p in conn.curseur_obj.historique
                 if "INSERT INTO presences" in s][-1]
    # (eleve_id, classe_id, statut, justifie, date)
    assert insertion[2] == "En retard"
    assert insertion[3] == "Oui"


# ============================================================
# COMPTES / PARAMETRES / PLANNING / ANNEES
# ============================================================

def test_post_compte_forme_bureau(client):
    c, _ = client
    r = c.post("/comptes", json={"nom": "Directeur Ecole", "email": "dir@ecole.cg",
                                 "telephone": "066000999", "role": "directeur",
                                 "actif": 1})
    assert r.status_code == 200, r.text
    assert r.json()["identifiant"] == "dir"


def test_parametres_et_planning(client):
    c, _ = client
    assert c.post("/parametre", json={"cle": "ville", "valeur": "Brazzaville"}).status_code == 200
    assert c.delete("/parametre/ville").status_code == 200
    assert c.post("/planning", json={"classe_id": 1, "jour": "Lundi",
                                     "creneau": "08h-10h", "matiere": "Maths",
                                     "salle": "B12"}).status_code == 200
    assert c.delete("/planning/1").status_code == 200
    # Le repli COUNT(*) de la fausse base renvoie 0
    assert c.get("/total_classe").json() == {"total_classe": 0}


def test_activation_annee_exclusive(client):
    c, conn = client
    avant = len(conn.curseur_obj.historique)
    r = c.put("/annee_scolaire/2/actif")
    assert r.status_code == 200, r.text
    recents = [s for s, _ in conn.curseur_obj.historique[avant:]]
    i_off = recents.index("UPDATE annee_scolaire SET est_active = FALSE")
    i_on = next(i for i, s in enumerate(recents)
                if "est_active = TRUE WHERE id = %s" in s)
    assert i_off < i_on


# ============================================================
# ROUTES HISTORIQUES NON CASSEES
# ============================================================

def test_routes_historiques_toujours_la(client):
    c, _ = client
    assert c.get("/ping").json() == {"status": "online"}
    assert c.get("/total_eleves").status_code == 200


# ============================================================
# SECURITE : RATE LIMITING, AUDIT, PROTECTION /audit
# ============================================================

import time

import jwt as pyjwt
import securite


@pytest.fixture(autouse=True)
def _limiteur_propre():
    securite.limiteur_connexion.reinitialiser()
    yield
    securite.limiteur_connexion.reinitialiser()


def test_rate_limit_login_bloque_apres_5_echecs(client):
    c, _ = client
    for _ in range(securite.LimiteurConnexion().max_echecs):
        r = c.post("/login", json={"identifiant": "pirate", "mot_de_passe": "x"})
        assert r.status_code == 401
    # 6eme tentative : bloque avant meme de toucher la base
    r = c.post("/login", json={"identifiant": "pirate", "mot_de_passe": "x"})
    assert r.status_code == 429


def test_rate_limit_par_identifiant_independant(client):
    c, _ = client
    for _ in range(5):
        c.post("/login", json={"identifiant": "pirate", "mot_de_passe": "x"})
    # Un autre identifiant n'herit pas du blocage
    r = c.post("/login", json={"identifiant": "directeur", "mot_de_passe": "x"})
    assert r.status_code == 401


def test_audit_ecrit_les_actions_sensibles(client):
    c, conn = client
    c.delete("/eleve/7/paiements")
    c.put("/modifierEleve/7", json={"pere_nom": "Nouveau Pere"})
    actions = [p[1] for s, p in conn.curseur_obj.historique
               if s.startswith("INSERT INTO audit_log")]
    assert "suppression_donnees_eleve" in actions
    assert "modification_eleve" in actions


def test_connexion_reussie_est_auditee(client):
    import bcrypt as bcrypt_mod
    hache = bcrypt_mod.hashpw(b"secret123", bcrypt_mod.gensalt()).decode()
    # /login utilise un curseur dictionary=True : ligne sous forme de dict
    ligne_utilisateur = {"id": 1, "nom": "DIALLO", "prenom": "Awa",
                         "telephone": "066000111", "email": None,
                         "mot_de_passe": hache, "role": "admin",
                         "statut": "actif"}
    motif = ("from utilisateur", [ligne_utilisateur])
    REPONSES.append(motif)
    try:
        c, conn = client
        r = c.post("/login", json={"identifiant": "066000111",
                                   "mot_de_passe": "secret123"})
        assert r.status_code == 200, r.text
        actions = [p[1] for s, p in conn.curseur_obj.historique
                   if s.startswith("INSERT INTO audit_log")]
        assert actions[-1] == "connexion_reussie"
    finally:
        REPONSES.remove(motif)


def test_consultation_audit_protegee(client):
    c, _ = client
    assert c.get("/audit").status_code == 401  # pas de token

    def token(role):
        return {"Authorization": "Bearer " + pyjwt.encode(
            {"user_id": 1, "role": role, "exp": time.time() + 3600},
            securite.SECRET_KEY, algorithm=securite.ALGORITHM)}

    assert c.get("/audit", headers=token("gestionnaire")).status_code == 403
    r = c.get("/audit", headers=token("admin"))
    assert r.status_code == 200 and r.json() == []
    # Token falsifie : signature invalide -> 401
    faux = {"Authorization": "Bearer " + pyjwt.encode(
        {"user_id": 9, "role": "admin", "exp": time.time() + 3600},
        "x" * 40, algorithm="HS256")}
    assert c.get("/audit", headers=faux).status_code == 401


def test_charger_secret_jwt_priorites(tmp_path, monkeypatch):
    monkeypatch.delenv("GS_JWT_SECRET", raising=False)

    # 1. Generation + persistance dans le dossier fourni
    secret1 = securite.charger_secret_jwt(dossier=str(tmp_path))
    assert len(secret1) >= 32
    fichier = tmp_path / ".jwt_secret"
    assert fichier.read_text(encoding="utf-8").strip() == secret1
    # 2. Relecture : le meme secret est retourn (persistance)
    assert securite.charger_secret_jwt(dossier=str(tmp_path)) == secret1

    # 3. Variable d'environnement trop courte -> refus explicite
    monkeypatch.setenv("GS_JWT_SECRET", "court")
    with pytest.raises(ValueError):
        securite.charger_secret_jwt(dossier=str(tmp_path))

    # 4. Variable d'environnement valide -> prioritaire
    monkeypatch.setenv("GS_JWT_SECRET", "x" * 48)
    assert securite.charger_secret_jwt(dossier=str(tmp_path)) == "x" * 48
