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


class TestStatutTraduit:
    """Le serveur renvoie actif / inactif / exclu ; l'interface filtre sur
    « Inscrit / Pre-inscrit / Inactif ». Sans traduction, un eleve rapatrie
    etait invisible sous tous les filtres."""

    def test_vocabulaire_serveur_traduit(self):
        from services.sync_service import _statut_eleve_local as t
        assert t("actif") == "Inscrit"
        assert t("inactif") == "Inactif"
        assert t("exclu") == "Inactif"
        assert t("radié") == "Inactif"
        assert t("pré-inscrit") == "Pre-inscrit"
        assert t(None) == "Inscrit"

    def test_vocabulaire_local_conserve(self):
        from services.sync_service import _statut_eleve_local as t
        assert t("Inscrit") == "Inscrit"
        assert t("Pre-inscrit") == "Pre-inscrit"
        assert t("Inactif") == "Inactif"

    def test_valeurs_acceptees_par_le_filtre_ui(self):
        from services.sync_service import _statut_eleve_local as t
        # Mots exacts du filtre de la page Eleves
        for serveur in ("actif", "inactif", "exclu", "radié", "inconnu"):
            assert t(serveur) in ("Inscrit", "Pre-inscrit", "Inactif")


class TestRechercheInsensibleAuxAccents:
    """« KONE » doit trouver « KONÉ », quelle que soit la casse."""

    def test_recherche_sans_accent_et_sans_casse(self, base_vierge):
        from repositories.eleve_repository import EleveRepository
        db = base_vierge
        db.execute("INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
                   ("ELEV20260001", "KONÉ", "Basile"))
        db.execute("INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
                   ("ELEV20260002", "Mbemba", "Jean"))
        repo = EleveRepository()
        assert [e["prenom"] for e in repo.eleves(recherche="kone")] == ["Basile"]
        assert [e["prenom"] for e in repo.eleves(recherche="KONÉ")] == ["Basile"]
        assert [e["prenom"] for e in repo.eleves(recherche="Kone")] == ["Basile"]
        # recherche par prenom seul
        assert [e["nom"] for e in repo.eleves(recherche="jean")] == ["Mbemba"]
        # matricule
        assert [e["nom"] for e in repo.eleves(recherche="0002")] == ["Mbemba"]
        # aucun resultat
        assert repo.eleves(recherche="inexistant") == []

    def test_recherche_avec_accent_dans_la_saisie(self, base_vierge):
        from repositories.eleve_repository import EleveRepository
        db = base_vierge
        db.execute("INSERT INTO eleves (matricule, nom, prenom) VALUES (?, ?, ?)",
                   ("ELEV20260001", "Mbemba", "Jean"))
        repo = EleveRepository()
        assert repo.eleves(recherche="mbemba") != []


class TestExportCSVSur:
    def test_formule_neutralisee(self):
        from services.csvsafe import csv_sur
        assert csv_sur("=cmd|' /C calc'!A1").startswith("'=")
        assert csv_sur("+1").startswith("'+")
        assert csv_sur("@SUM(A1)").startswith("'@")
        assert csv_sur("-5").startswith("'-")

    def test_placeholder_et_valeurs_normales_inchangees(self):
        from services.csvsafe import csv_sur
        assert csv_sur("-") == "-"
        assert csv_sur("KONÉ") == "KONÉ"
        assert csv_sur("Basile") == "Basile"
        assert csv_sur("") == ""
        assert csv_sur(None) == ""

    def test_reports_reexporte_le_meme_helper(self):
        from services import reports
        assert reports.csv_sur("=1") == "'=1"
