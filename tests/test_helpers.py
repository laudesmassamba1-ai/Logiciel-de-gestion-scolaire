import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.pages.helpers import _appreciation, _parse_money


def _db_module():
    """Retourne le MODULE database.db.

    `import database.db as m` est errone : database/__init__.py exporte la
    variable `db = Database()` qui masque le sous-module `db`, donc `m.DB_PATH`
    leve AttributeError ('Database' object has no attribute 'DB_PATH')."""
    import importlib
    return importlib.import_module("database.db")


class TestAppreciation:
    """Tests des valeurs par defaut via le module central."""

    def setup_method(self):
        import os, tempfile
        self._tmpdir = tempfile.mkdtemp()
        db_mod = _db_module()
        self._old_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = Path(os.path.join(self._tmpdir, "ecole.db"))
        self._db = db_mod.Database()
        self._db._initialized = False
        self._db.init_db()

    def teardown_method(self):
        import os, shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        db_mod = _db_module()
        if self._old_db_path is not None:
            db_mod.DB_PATH = self._old_db_path
        self._db._initialized = False

    def test_excellent(self):
        assert _appreciation(16) == "Excellent"
        assert _appreciation(20) == "Excellent"

    def test_tres_bien(self):
        assert _appreciation(14) == "Tres bien"
        assert _appreciation(15.9) == "Tres bien"

    def test_bien(self):
        assert _appreciation(12) == "Bien"
        assert _appreciation(13.9) == "Bien"

    def test_assez_bien(self):
        assert _appreciation(10) == "Assez bien"
        assert _appreciation(11.9) == "Assez bien"

    def test_passable(self):
        assert _appreciation(8) == "Passable"
        assert _appreciation(9.9) == "Passable"

    def test_insuffisant(self):
        assert _appreciation(0) == "Insuffisant"
        assert _appreciation(7.9) == "Insuffisant"

    def test_none_returns_dash(self):
        assert _appreciation(None) == "-"


class TestAppreciationsConfigurable:
    def setup_method(self):
        import os, tempfile
        self._tmpdir = tempfile.mkdtemp()
        db_mod = _db_module()
        self._old_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = Path(os.path.join(self._tmpdir, "ecole.db"))
        self._db = db_mod.Database()
        self._db._initialized = False
        self._db.init_db()

    def teardown_method(self):
        import os, shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        db_mod = _db_module()
        if self._old_db_path is not None:
            db_mod.DB_PATH = self._old_db_path
        self._db._initialized = False

    def test_defaults(self):
        from services.appreciations import lire_config, appreciation
        config = lire_config()
        assert len(config) == 6
        assert config[0]["libelle"] == "Excellent"
        assert config[-1]["libelle"] == "Insuffisant"
        assert appreciation(17) == "Excellent"
        assert appreciation(7) == "Insuffisant"

    def test_custom_config(self):
        from services.appreciations import enregistrer_config, lire_config, appreciation
        enregistrer_config([
            {"seuil": 18, "libelle": "Distinction"},
            {"seuil": 15, "libelle": "Mention"},
            {"seuil": 0, "libelle": "Echec"},
        ])
        config = lire_config()
        assert len(config) == 3
        assert config[0]["libelle"] == "Distinction"
        assert appreciation(19) == "Distinction"
        assert appreciation(16) == "Mention"
        assert appreciation(11) == "Echec"

    def test_empty_config_resets_to_defaults(self):
        from services.appreciations import enregistrer_config, lire_config
        enregistrer_config([])
        config = lire_config()
        assert len(config) == 6

    def test_invalid_json_falls_back_to_defaults(self):
        self._db.execute(
            "INSERT OR REPLACE INTO parametres (cle, valeur) VALUES (?, ?)",
            ("appreciations_config", "NOT JSON"))
        from services.appreciations import lire_config
        config = lire_config()
        assert len(config) == 6

    def test_sorted_by_seuil_desc(self):
        from services.appreciations import enregistrer_config, lire_config
        enregistrer_config([
            {"seuil": 0, "libelle": "Echec"},
            {"seuil": 18, "libelle": "Haut"},
            {"seuil": 10, "libelle": "Moyen"},
        ])
        config = lire_config()
        seuils = [p["seuil"] for p in config]
        assert seuils == sorted(seuils, reverse=True)


class TestParseMoney:
    def test_integer(self):
        assert _parse_money("25000") == 25000.0

    def test_with_suffix(self):
        assert _parse_money("25000 FCFA") == 25000.0

    def test_with_spaces(self):
        assert _parse_money("25 000") == 25000.0

    def test_comma_thousands(self):
        assert _parse_money("25 000") == 25000.0

    def test_empty_string(self):
        assert _parse_money("") == 0.0

    def test_none(self):
        assert _parse_money(None) == 0.0

    def test_zero(self):
        assert _parse_money("0") == 0.0
