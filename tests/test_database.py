import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def reset_db_singleton():
    from database.db import Database
    Database._instance = None
    yield
    Database._instance = None


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    import sys
    import core.config
    import importlib
    db_mod = sys.modules["database.db"] if "database.db" in sys.modules else importlib.import_module("database.db")
    monkeypatch.setattr(core.config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(core.config, "DOCS_DIR", tmp_path / "documents")

    Database = db_mod.Database
    Database._instance = None
    db = Database()
    db.init_db()
    yield db
    Database._instance = None


class TestDatabaseInit:
    def test_creates_tables(self, test_db):
        tables = test_db.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        names = [t["name"] for t in tables]
        assert "utilisateurs" in names
        assert "classes" in names
        assert "eleves" in names
        assert "notes" in names
        assert "presences" in names
        assert "matieres" in names
        assert "parametres" in names

    def test_seeds_users_empty(self, test_db):
        users = test_db.query("SELECT COUNT(*) AS c FROM utilisateurs")
        assert users[0]["c"] == 0

    def test_seeds_matieres(self, test_db):
        matieres = test_db.query("SELECT nom FROM matieres ORDER BY nom")
        noms = [m["nom"] for m in matieres]
        assert "Mathematiques" in noms
        assert "Francais" in noms

    def test_seeds_parametres(self, test_db):
        params = test_db.query("SELECT cle, valeur FROM parametres ORDER BY cle")
        keys = {p["cle"] for p in params}
        assert "signataire_nom" in keys
        assert "ville" in keys
        assert "pays" in keys

    def test_seeds_annees_scolaires(self, test_db):
        annees = test_db.query("SELECT * FROM annees_scolaires")
        assert len(annees) >= 1

    def test_seeds_cycles(self, test_db):
        cycles = test_db.query("SELECT nom FROM cycles ORDER BY nom")
        noms = [c["nom"] for c in cycles]
        assert "Primaire" in noms
        assert "College" in noms

    def test_seeds_classes(self, test_db):
        classes = test_db.query("SELECT nom FROM classes ORDER BY nom")
        assert len(classes) >= 10


class TestDatabaseQuery:
    def test_query_one_found(self, test_db):
        test_db.execute(
            "INSERT INTO utilisateurs (nom_complet, username, password, role) VALUES (?, ?, ?, ?)",
            ("Test User", "testuser", "hashed", "gestionnaire"))
        user = test_db.query_one("SELECT * FROM utilisateurs WHERE username = 'testuser'")
        assert user is not None
        assert user["role"] == "gestionnaire"

    def test_query_one_not_found(self, test_db):
        user = test_db.query_one("SELECT * FROM utilisateurs WHERE username = 'nonexistent'")
        assert user is None

    def test_query_returns_dicts(self, test_db):
        test_db.execute(
            "INSERT INTO utilisateurs (nom_complet, username, password, role) VALUES (?, ?, ?, ?)",
            ("Dict User", "dictuser", "hashed", "gestionnaire"))
        rows = test_db.query("SELECT * FROM utilisateurs LIMIT 1")
        assert isinstance(rows, list)
        assert isinstance(rows[0], dict)

    def test_execute_returns_lastrowid(self, test_db):
        row_id = test_db.execute(
            "INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
            ("EXLQR001", "Test", "Eleve"))
        assert row_id is not None
        assert row_id > 0

    def test_executemany(self, test_db):
        test_db.executemany(
            "INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
            [("EMQR001", "A", "B"), ("EMQR002", "C", "D")])
        count = test_db.query_one("SELECT COUNT(*) as c FROM eleves WHERE matricule IN ('EMQR001', 'EMQR002')")
        assert count["c"] == 2

    def test_query_with_params(self, test_db):
        test_db.execute(
            "INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
            ("QPQR001", "Dupont", "Jean"))
        result = test_db.query_one("SELECT * FROM eleves WHERE matricule = ?", ("QPQR001",))
        assert result is not None
        assert result["nom"] == "Dupont"

    def test_idempotent_init(self, test_db):
        test_db.init_db()
        users = test_db.query("SELECT COUNT(*) as c FROM utilisateurs")
        assert users[0]["c"] == 0
