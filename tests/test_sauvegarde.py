"""Tests de la sauvegarde automatique des bases (app + serveur).

Couvre `services/sauvegarde.py` : copie consistante, journal, rotation,
declenchement quotidien et a la fermeture (via main.py).
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def dossier(monkeypatch, tmp_path):
    """isole la donnee (GS_DATA_DIR) et re-importe le module sauvegarde."""
    monkeypatch.setenv("GS_DATA_DIR", str(tmp_path))
    # base app + base serveur
    datadir = tmp_path / "data"
    datadir.mkdir(parents=True, exist_ok=True)
    (datadir / "serveur").mkdir(parents=True, exist_ok=True)

    def _creer_base(chemin, table="x", ligne="valeur"):
        conn = sqlite3.connect(str(chemin))
        conn.execute(f"CREATE TABLE {table} (k TEXT)")
        conn.execute(f"INSERT INTO {table} VALUES (?)", (ligne,))
        conn.commit()
        conn.close()

    _creer_base(datadir / "ecole.db", "eleves", "ADA")
    _creer_base(datadir / "serveur" / "serveur_gs.db", "notes", "13,5")

    import services.sauvegarde as sauvegarde
    return sauvegarde, datadir


class TestSauvegardeAutomatique:
    def test_sauvegarde_copie_les_deux_bases(self, dossier):
        sauvegarde, datadir = dossier
        resultat = sauvegarde.sauvegarder_maintenant("test")
        assert resultat["n"] == 2
        copie = list((datadir / "sauvegardes").glob("ecole-*test.db"))
        assert len(copie) == 1
        conn = sqlite3.connect(str(copie[0]))
        assert conn.execute("SELECT k FROM eleves").fetchone()[0] == "ADA"
        conn.close()

    def test_copie_preserve_donnees_serveur(self, dossier):
        sauvegarde, datadir = dossier
        sauvegarde.sauvegarder_maintenant("test")
        copie = list((datadir / "sauvegardes").glob("serveur_gs-*test.db"))
        assert len(copie) == 1
        conn = sqlite3.connect(str(copie[0]))
        assert conn.execute("SELECT k FROM notes").fetchone()[0] == "13,5"
        conn.close()

    def test_journal_ecrit(self, dossier):
        sauvegarde, datadir = dossier
        sauvegarde.sauvegarder_maintenant("test")
        journal = datadir / "sauvegardes" / "journal.csv"
        assert journal.exists()
        contenu = journal.read_text(encoding="utf-8")
        assert "test" in contenu and "ok" in contenu

    def test_rotation_garde_les_plus_recentes(self, dossier):
        sauvegarde, datadir = dossier
        dossier_sauv = datadir / "sauvegardes"
        dossier_sauv.mkdir(parents=True, exist_ok=True)
        for i in range(35):
            jour = f"20200101-{i:06d}"
            (dossier_sauv / f"ecole-{jour}-test.db").write_text("x")
        sauvegarde._rotationner("ecole")
        restantes = list(dossier_sauv.glob("ecole-*-test.db"))
        assert len(restantes) == sauvegarde.ROTATION

    def test_quotidien_une_seule_fois_par_jour(self, dossier):
        sauvegarde, datadir = dossier
        date_str = datetime.now().strftime("%Y%m%d")

        sauvegarde.sauvegarder_si_quotidien()
        nb_apres_1 = len(list((datadir / "sauvegardes").glob(
            f"ecole-{date_str}-*")))

        sauvegarde.sauvegarder_si_quotidien()
        nb_apres_2 = len(list((datadir / "sauvegardes").glob(
            f"ecole-{date_str}-*")))
        assert nb_apres_1 == 1 and nb_apres_2 == 1

    def test_a_la_fermeture(self, dossier):
        sauvegarde, datadir = dossier
        sauvegarde.sauvegarder_maintenant("fermeture")
        assert list((datadir / "sauvegardes").glob("ecole-*fermeture.db"))