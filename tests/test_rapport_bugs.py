"""Tests de non-regression pour les correctifs issus de RAPPORT_BUGS.md."""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def base_vierge(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)
    monkeypatch.setenv("GS_DATA_DIR", str(data))
    import database.db
    db_module = sys.modules["database.db"]
    monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
    monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
    from database import db
    db._initialized = False
    db.init_db()
    yield db
    db._initialized = False


def _en_ligne(monkeypatch):
    from core import network
    monkeypatch.setattr(network, "_sync_active", True, raising=False)
    monkeypatch.setattr(network, "_state", "online")


def _patch_request(monkeypatch, fake):
    """Patche _request sur le vrai module api.client (le package 'api'
    masque l'attribut client avec une instance ApiClient)."""
    import importlib
    mod = importlib.import_module("api.client")
    monkeypatch.setattr(mod, "_request", fake)


# ----------------------------------------------------------------------
# Bug 28 : dedoublonnage de la file d'attente
# ----------------------------------------------------------------------

class TestEnqueueDedup:

    def test_meme_operation_une_seule_fois(self, base_vierge):
        payload = json.dumps({"nom": "6eme A"}, ensure_ascii=False)
        base_vierge.enqueue("POST", "/classe", payload, uuid_client="u-1")
        base_vierge.enqueue("POST", "/classe", payload, uuid_client="u-1")
        assert len(base_vierge.dequeue_pending()) == 1

    def test_operations_differentes_conservees(self, base_vierge):
        p1 = json.dumps({"nom": "6eme A"})
        p2 = json.dumps({"nom": "5eme A"})
        base_vierge.enqueue("POST", "/classe", p1)
        base_vierge.enqueue("POST", "/classe", p2)
        assert len(base_vierge.dequeue_pending()) == 2


# ----------------------------------------------------------------------
# Bugs 21 / 41 : UUID stable + classe Parent supprimee
# ----------------------------------------------------------------------

class TestModelsEleve:

    def test_uuid_stable_entre_deux_appels(self):
        from models.eleve import Eleve
        eleve = Eleve(nom="Mbemba", prenom="Grace")
        premier = eleve.to_dict()["uuid_client"]
        second = eleve.to_dict()["uuid_client"]
        assert premier and premier == second

    def test_classe_parent_supprimee(self):
        import models.eleve as mod
        assert not hasattr(mod, "Parent")


# ----------------------------------------------------------------------
# Bugs 2 / 12 : retry avant mise en file ; ecriture locale conservee
# ----------------------------------------------------------------------

class TestRouteWrite:

    @staticmethod
    def _repo():
        from repositories.base import RepositoryBase

        class Repo(RepositoryBase):
            pass

        return Repo()

    def test_succes_api_ne_met_pas_en_file_mais_ecrit_localement(
            self, base_vierge, monkeypatch):
        _en_ligne(monkeypatch)
        _patch_request(monkeypatch, lambda *a, **k: ({"ok": 1}, None))
        local = []
        self._repo()._route_write("POST", "/x", {"a": 1},
                                  local.append, "ok")
        assert local == ["ok"]
        assert base_vierge.dequeue_pending() == []

    def test_echec_puis_succes_pas_de_file(self, base_vierge, monkeypatch):
        _en_ligne(monkeypatch)
        appels = {"n": 0}

        def _request_fake(*a, **k):
            appels["n"] += 1
            if appels["n"] == 1:
                return (None, "timeout")
            return ({"ok": 1}, None)

        _patch_request(monkeypatch, _request_fake)
        local = []
        self._repo()._route_write("POST", "/x", {"a": 1},
                                  local.append, "ok")
        assert appels["n"] == 2
        assert base_vierge.dequeue_pending() == []

    def test_echec_repete_enfile_une_seule_fois(self, base_vierge,
                                                monkeypatch):
        _en_ligne(monkeypatch)
        _patch_request(monkeypatch,
                            lambda *a, **k: (None, "serveur injoignable"))
        local = []
        self._repo()._route_write("POST", "/x", {"a": 1},
                                  local.append, "ok")
        assert local == ["ok"]
        assert len(base_vierge.dequeue_pending()) == 1


# ----------------------------------------------------------------------
# Bug 39 : planning sauvegarde en une seule transaction
# ----------------------------------------------------------------------

class TestPlanningTransaction:

    def test_echec_insertion_conserve_ancien_planning(self, base_vierge,
                                                      monkeypatch):
        from repositories.planning_repository import PlanningRepository
        repo_p = PlanningRepository()
        monkeypatch.setattr(repo_p, "_route_write", lambda *a, **k: None)

        repo_p.save_planning(3, [("Lundi", "08:00-10:00", "Maths", "B1")])
        avant = base_vierge.query("SELECT * FROM planning WHERE classe_id = 3")
        assert len(avant) == 1

        with pytest.raises(sqlite3.DatabaseError):
            # objet non liable -> echec au milieu de la transaction.
            repo_p.save_planning(3, [("Mardi", "08:00-10:00", "SVT", object())])
        apres = base_vierge.query("SELECT * FROM planning WHERE classe_id = 3")
        assert len(apres) == 1  # ROLLBACK : l'ancien planning est intact


# ----------------------------------------------------------------------
# Bug 22 : upgrade silencieux des hash SHA-256 nus a la connexion
# ----------------------------------------------------------------------

class TestUpgradeHashLegacy:

    @staticmethod
    def _creer_ancien_compte(db, username):
        vieux = hashlib.sha256("secret123".encode()).hexdigest()
        db.execute(
            """INSERT INTO utilisateurs (nom_complet, username, password, role, actif)
               VALUES ('Ancien', ?, ?, 'directeur', 1)""", (username, vieux))

    def test_login_upgrade_vieux_hash(self, base_vierge):
        from services.auth import AuthService
        self._creer_ancien_compte(base_vierge, "ancien")
        user, err = AuthService().login("ancien", "secret123")
        assert err is None and user is not None
        stocke = base_vierge.query_one(
            "SELECT password FROM utilisateurs WHERE username='ancien'")
        assert ":" in stocke["password"]

    def test_login_refuse_hash_legacy_invalide(self, base_vierge):
        from services.auth import AuthService
        self._creer_ancien_compte(base_vierge, "ancien2")
        _, err = AuthService().login("ancien2", "mauvais")
        assert err is not None


# ----------------------------------------------------------------------
# Bug 10 : suppression propagee uniquement sans donnees rattachees
# ----------------------------------------------------------------------

class TestSyncSuppressions:

    @staticmethod
    def _patch_client(monkeypatch, cycles=(), classes=(), matieres=()):
        from types import SimpleNamespace
        import api  # le package expose 'client' = instance ApiClient
        fake = SimpleNamespace(
            cycles=lambda: (list(cycles), None),
            classes=lambda: (list(classes), None),
            matieres=lambda: (list(matieres), None),
            lister_annees_scolaires=lambda: ([], None),
            annee_scolaire_active=lambda: (None, "aucune"),
            tarifs_scolarite=lambda: ([], None))
        monkeypatch.setattr(api, "client", fake)

    def test_classe_vide_absente_du_serveur_supprimee(self, base_vierge,
                                                      monkeypatch):
        from services.sync_service import pull_structure
        self._patch_client(monkeypatch, cycles=[{"id": 1, "nom": "College"}],
                           classes=[{"id": 1, "nom": "5eme", "cycle_id": 1}])
        resultat = pull_structure()
        noms = [c["nom"] for c in base_vierge.query("SELECT nom FROM classes")]
        # Les classes seedees vides absentes du serveur sont retirees.
        assert "6eme" not in noms
        assert "5eme" in noms
        assert resultat["suppressions"] >= 1

    def test_classe_avec_eleves_jamais_supprimee(self, base_vierge,
                                                 monkeypatch):
        from services.sync_service import pull_structure
        self._patch_client(monkeypatch, cycles=[{"id": 1, "nom": "College"}],
                           classes=[{"id": 1, "nom": "5eme", "cycle_id": 1}])
        base_vierge.execute(
            """INSERT INTO eleves (matricule, nom, prenom, classe_id)
               VALUES ('MAT-TEST', 'Nzaba', 'Ali',
                       (SELECT id FROM classes WHERE nom='6eme'))""")
        pull_structure()
        noms = [c["nom"] for c in base_vierge.query("SELECT nom FROM classes")]
        assert "6eme" in noms  # gardee : des eleves y sont rattaches

    def test_cycle_avec_classes_jamais_supprime(self, base_vierge,
                                                monkeypatch):
        from services.sync_service import pull_structure
        self._patch_client(monkeypatch, cycles=[{"id": 9, "nom": "Lycee"}],
                           classes=[{"id": 9, "nom": "2nde", "cycle_id": 9}])
        resultat = pull_structure()
        noms = [c["nom"] for c in base_vierge.query("SELECT nom FROM cycles")]
        for garde in ("Prescolaire", "Primaire", "College"):
            assert garde in noms  # leurs classes seedees existent encore


# ----------------------------------------------------------------------
# Bugs 42 / 49 : parse money explicite ; masse salariale sans inactifs
# ----------------------------------------------------------------------

class TestDivers:

    def test_parse_money_cas_limites(self):
        from ui.pages.helpers import _parse_money
        assert _parse_money("") == 0.0
        assert _parse_money("FCFA") == 0.0
        assert _parse_money("abc") == 0.0
        assert _parse_money(None) == 0.0
        assert _parse_money("25 000 FCFA") == 25000.0
        assert _parse_money("25,500") == 25500.0

    def test_masse_salariale_exclut_inactifs(self, base_vierge):
        base_vierge.execute(
            """INSERT INTO personnel (nom_complet, fonction, salaire, statut)
               VALUES ('A', 'Gardien', 100000, 'Contrat')""")
        base_vierge.execute(
            """INSERT INTO personnel (nom_complet, fonction, salaire, statut)
               VALUES ('B', 'Surveillant', 50000, 'inactif')""")
        total = base_vierge.query_one(
            "SELECT COALESCE(SUM(salaire), 0) AS s FROM personnel "
            "WHERE statut IS NULL OR LOWER(statut) != 'inactif'")["s"]
        assert total == 100000.0


# ----------------------------------------------------------------------
# Bug 1 : tripwire — plus aucun appel .dict() Pydantic v1 dans le serveur
# ----------------------------------------------------------------------

def test_serveur_sans_pydantic_dict():
    for fichier in ("server/main.py", "server/compat.py"):
        source = Path(fichier).read_text(encoding="utf-8")
        assert ".dict()" not in source, f"{fichier} utilise encore .dict()"
