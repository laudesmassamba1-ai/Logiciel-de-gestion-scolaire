import sys

import pytest


@pytest.fixture()
def base_vierge(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)
    monkeypatch.setenv("GS_DATA_DIR", str(tmp_path))
    import database.db
    db_module = sys.modules["database.db"]
    monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
    monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
    from database import db
    db._initialized = False
    db.init_db()
    yield db
    db._initialized = False


class TestCollisionMatricule:
    """Critique 1 : deux postes peuvent generer le meme matricule (MAX+1
    local). L'insertion heurte alors la contrainte UNIQUE de la base locale ;
    add_eleve doit regenere un numero et reessayer, sans traceback."""

    def test_add_eleve_regenerait_le_matricule_apres_collision(self, base_vierge):
        from repositories.eleve_repository import EleveRepository
        db = base_vierge
        # Le matricule ELEV20260001 existe deja (genere par un autre poste
        # rapatrie via la sync).
        db.execute(
            "INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
            ("ELEV20260001", "Dupont", "Jean"))

        repo = EleveRepository()
        appels = {"n": 0}

        def faux_next_matricule():
            appels["n"] += 1
            return "ELEV20260001" if appels["n"] == 1 else "ELEV20260002"

        import unittest.mock as mock
        with mock.patch.object(repo, "next_matricule", side_effect=faux_next_matricule):
            nouvel_id = repo.add_eleve({"nom": "MBEMBA", "prenom": "Malo"})

        assert nouvel_id is not None
        ligne = db.query_one(
            "SELECT * FROM eleves WHERE matricule = 'ELEV20260002'")
        assert ligne is not None
        assert ligne["nom"] == "MBEMBA"
        assert appels["n"] == 2  # le premier numero etait pris, le second a marche
        # Aucun doublon de matricule ni d'élève.
        assert db.query("SELECT COUNT(*) c FROM eleves")[0]["c"] == 2

    def test_sans_collision_le_premier_matricule_est_garde(self, base_vierge):
        from repositories.eleve_repository import EleveRepository
        db = base_vierge
        repo = EleveRepository()
        with __import__("unittest").mock.patch.object(
                repo, "next_matricule", return_value="ELEV20260999"):
            nouvel_id = repo.add_eleve({"nom": "A", "prenom": "B"})
        assert nouvel_id is not None
        assert db.query_one(
            "SELECT 1 FROM eleves WHERE matricule = 'ELEV20260999'") is not None