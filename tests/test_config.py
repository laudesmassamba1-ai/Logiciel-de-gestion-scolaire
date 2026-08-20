import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import (
    APP_NAME, APP_VERSION, ROLES, ROLE_LABELS, PERIODES, JOURS,
    C_PRIMARY, C_TEXT, DB_PATH, DOCS_DIR, data_dir, resource_path,
    DEFAULT_MATIERES,
)


class TestConfig:
    def test_app_name(self):
        assert APP_NAME == "Gestion Scolaire"

    def test_app_version_format(self):
        parts = APP_VERSION.split(".")
        assert len(parts) == 3

    def test_roles_tuple(self):
        assert "directeur" in ROLES
        assert "gestionnaire" in ROLES

    def test_role_labels(self):
        assert ROLE_LABELS["directeur"] == "Directeur"
        assert ROLE_LABELS["gestionnaire"] == "Gestionnaire"

    def test_periodes(self):
        assert len(PERIODES) == 3

    def test_jours(self):
        assert len(JOURS) == 6

    def test_colors_are_hex(self):
        assert C_PRIMARY.startswith("#")
        assert C_TEXT.startswith("#")

    def test_db_path_is_path(self):
        assert isinstance(DB_PATH, Path)
        assert DB_PATH.name == "ecole.db"

    def test_docs_dir_is_path(self):
        assert isinstance(DOCS_DIR, Path)

    def test_data_dir_returns_path(self):
        d = data_dir()
        assert isinstance(d, Path)
        assert d.exists()

    def test_resource_path(self):
        p = resource_path("ui/ui_files")
        assert isinstance(p, Path)

    def test_default_matieres_count(self):
        assert len(DEFAULT_MATIERES) >= 6
