import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCoherenceAnneeScolaire:
    """Garde temporelle : aucune ecriture datee hors annee scolaire active."""

    @pytest.fixture()
    def base_vierge(self, tmp_path, monkeypatch):
        data = tmp_path / "data"
        data.mkdir(parents=True)
        monkeypatch.setenv("GS_DATA_DIR", str(tmp_path))
        import database.db  # garantit le chargement du sous-module
        db_module = sys.modules["database.db"]
        monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
        monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
        from database import db
        db._initialized = False
        db.init_db()
        yield db
        db._initialized = False

    def _definir_annee(self, db, libelle, debut, fin):
        db.execute("UPDATE annees_scolaires SET est_active = 0")
        return db.execute(
            "INSERT INTO annees_scolaires (libelle, date_debut, date_fin, est_active)"
            " VALUES (?, ?, ?, 1)", (libelle, debut, fin))

    def test_date_dans_annee_active_accepte_interieur(self, base_vierge):
        from ui.pages.helpers import date_dans_annee_active
        self._definir_annee(base_vierge, "2025-2026", "2025-09-01", "2026-06-30")
        assert date_dans_annee_active("2025-12-15") is True
        assert date_dans_annee_active("2025-09-01") is True  # bornes incluses
        assert date_dans_annee_active("2026-06-30") is True

    def test_date_hors_annee_active_refusee(self, base_vierge):
        from ui.pages.helpers import date_dans_annee_active
        self._definir_annee(base_vierge, "2025-2026", "2025-09-01", "2026-06-30")
        # Le cas remonte par l'utilisateur : annee recente activee,
        # saisies anterieures a la rentree.
        assert date_dans_annee_active("2020-10-05") is False
        assert date_dans_annee_active("2026-07-01") is False

    def test_transaction_rattachee_a_l_annee_active(self, base_vierge):
        self._definir_annee(base_vierge, "2024-2025", "2024-09-01", "2025-06-30")
        reference = repos_add_transaction()
        row = base_vierge.query_one(
            "SELECT * FROM transactions WHERE reference = ?", (reference,))
        assert row["annee_scolaire"] == "2024-2025"

    def test_filtrage_caisse_par_annee_conserve_l_historique_sans_annee(self, base_vierge):
        self._definir_annee(base_vierge, "2024-2025", "2024-09-01", "2025-06-30")
        repos_add_transaction()  # rattachee a 2024-2025
        # Ligne historique sans annee (saisies d'avant la migration).
        base_vierge.execute(
            "UPDATE transactions SET annee_scolaire = NULL")
        from repositories import repos
        filtre_actif = repos.transactions(annee="2024-2025")
        assert len(filtre_actif) == 1  # l'historique reste visible
        toutes = repos.transactions(annee=None)
        assert len(toutes) == 1


def repos_add_transaction():
    from repositories import repos
    return repos.add_transaction(
        "entree", 5000, "Droits de scolarite", "Scolarite",
        "Eleve Test", "Especes")
