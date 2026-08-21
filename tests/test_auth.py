import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth import RoleAuthorizer


class TestRoleAuthorizer:
    def test_directeur_can_access_comptes(self):
        auth = RoleAuthorizer("directeur")
        assert auth.can_edit("comptes") is True

    def test_directeur_can_access_parametres(self):
        auth = RoleAuthorizer("directeur")
        assert auth.can_edit("parametres") is True

    def test_gestionnaire_cannot_access_parametres(self):
        auth = RoleAuthorizer("gestionnaire")
        assert auth.can_edit("parametres") is False

    def test_gestionnaire_cannot_access_personnel(self):
        auth = RoleAuthorizer("gestionnaire")
        assert auth.allowed("personnel") is False
        assert auth.can_edit("personnel") is False

    def test_gestionnaire_can_edit_notes(self):
        auth = RoleAuthorizer("gestionnaire")
        assert auth.can_edit("notes") is True

    def test_directeur_can_edit_notes(self):
        auth = RoleAuthorizer("directeur")
        assert auth.can_edit("notes") is True

    def test_directeur_allowed_comptes(self):
        auth = RoleAuthorizer("directeur")
        assert auth.allowed("comptes") is True

    def test_directeur_allowed_all_pages(self):
        auth = RoleAuthorizer("directeur")
        for page in ("dashboard", "stats", "eleves", "classes", "cycles", "notes",
                     "presences", "planning", "caisse", "tarifs", "paiements",
                     "personnel", "programmes", "parametres", "comptes"):
            assert auth.allowed(page) is True

    def test_gestionnaire_allowed_pages(self):
        auth = RoleAuthorizer("gestionnaire")
        for page in ("dashboard", "stats", "eleves", "classes", "cycles", "notes",
                     "presences", "planning", "caisse", "tarifs", "paiements",
                     "programmes"):
            assert auth.allowed(page) is True

    def test_gestionnaire_not_allowed_comptes(self):
        auth = RoleAuthorizer("gestionnaire")
        assert auth.allowed("comptes") is False

    def test_gestionnaire_denied_by_default(self):
        auth = RoleAuthorizer("gestionnaire")
        assert auth.allowed("page_inexistante") is False
        assert auth.can_edit("page_inexistante") is False

    def test_unknown_role_defaults_to_gestionnaire(self):
        auth = RoleAuthorizer("unknown_role")
        assert auth.role == "gestionnaire"
        assert auth.allowed("eleves") is True

    def test_random_password_length(self):
        from services.auth import AuthService
        svc = AuthService()
        pwd = svc.random_password()
        assert len(pwd) == 12
