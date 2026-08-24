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


class TestSessionPersistante:
    """Exigence : apres la creation du compte, plus jamais d'identification
    au lancement, sauf deconnexion volontaire via le bouton Dedconnexion."""

    @pytest.fixture()
    def base_vierge(self, tmp_path, monkeypatch):
        """Redirige la base vers un repertoire temporaire.

        database.db.connect() lit DB_PATH au moment de l'appel : il suffit
        de remplacer la variable globale du module (restauree par monkeypatch).
        """
        data = tmp_path / "data"
        data.mkdir(parents=True)
        monkeypatch.setenv("GS_DATA_DIR", str(tmp_path))
        import database.db  # garantit le chargement du sous-module
        db_module = sys.modules["database.db"]
        monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
        monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
        from database import db
        # Singleton : reautoriser la creation du schema dans la nouvelle base
        db._initialized = False
        db.init_db()
        yield db

    def _creer_compte(self, db):
        from database.db import hash_password
        uid = db.execute(
            "INSERT INTO utilisateurs (nom_complet, username, password, role, actif)"
            " VALUES (?, ?, ?, ?, 1)",
            ("Alice Directeur", "alice.directeur", hash_password("mdp-secret"),
             "directeur"))
        return db.query_one("SELECT * FROM utilisateurs WHERE id = ?", (uid,))

    def test_creation_compte_puis_reconnexions_automatiques(self, base_vierge):
        from services.auth import AuthService
        db = base_vierge
        auth = AuthService()
        assert not auth.has_accounts()

        user = self._creer_compte(db)
        auth.save_session(user["id"])

        # Relances successifs : aucun identifiant demande
        for _ in range(3):
            reconnecte = AuthService().get_saved_user()
            assert reconnecte is not None
            assert reconnecte["id"] == user["id"]

    def test_deconnexion_reclame_les_identifiants(self, base_vierge):
        from services.auth import AuthService
        db = base_vierge
        auth = AuthService()
        user = self._creer_compte(db)
        auth.save_session(user["id"])
        assert auth.get_saved_user() is not None

        # Clic sur le bouton Deconnexion -> MainWindow.logout() -> clear_session
        AuthService().clear_session()
        assert AuthService().get_saved_user() is None

    def test_login_manuel_persiste_pour_les_relances(self, base_vierge):
        from services.auth import AuthService
        db = base_vierge
        user = self._creer_compte(db)

        # Apres deconnexion : login manuel via LoginDialog._do_login
        auth = AuthService()
        connecte, erreur = auth.login("alice.directeur", "mdp-secret")
        assert connecte is not None and erreur is None
        auth.save_session(connecte["id"])

        # Les relances suivantes ne demandent plus rien
        assert AuthService().get_saved_user()["id"] == user["id"]

    def test_mauvais_mot_de_passe_apres_deconnexion(self, base_vierge):
        from services.auth import AuthService
        db = base_vierge
        self._creer_compte(db)
        auth = AuthService()
        connecte, _ = auth.login("alice.directeur", "MAUVAIS")
        assert connecte is None

    def test_flux_demande_connexion_main(self, base_vierge, monkeypatch):
        """E2E : main._demande_connexion respecte les trois scenarios."""
        import main as app_main
        from services.auth import AuthService
        db = base_vierge
        user = self._creer_compte(db)

        # S1 : creation du compte -> session sauvegardee -> entre direct
        AuthService().save_session(user["id"])

        class EspionLogin:
            Accepted = 1
            def __init__(self, *a, **k):
                raise AssertionError("Ecran de connexion affiche a tort !")
        monkeypatch.setattr(app_main, "LoginDialog", EspionLogin)
        reconnecte = app_main._demande_connexion()
        assert reconnecte is not None and reconnecte["id"] == user["id"]

        # S3 : apres deconnexion, l'ecran de connexion est exige
        AuthService().clear_session()
        try:
            app_main._demande_connexion()
            pytest.fail("Aucun ecran de connexion apres deconnexion")
        except AssertionError:
            pass  # EspionLogin declenche = l'ecran de connexion EST affiche
