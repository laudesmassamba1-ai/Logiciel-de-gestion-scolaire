import os
import sys
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from core.config import APP_NAME, APP_STYLESHEET, APP_FONT_FAMILY, APP_FONT_FALLBACK, APP_FONT_SIZE
from database import db
from services import auth_service as auth
from ui.login_view import FirstSetupDialog, LoginDialog
from ui.main_view import MainWindow


def _setup_high_dpi():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    os.environ["QT_USE_PHYSICAL_DPI"] = "0"
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def _pick_base_font() -> QFont:
    familles = list(APP_FONT_FALLBACK)
    if APP_FONT_FAMILY not in familles:
        familles.insert(0, APP_FONT_FAMILY)
    disponibles = set(QFontDatabase().families())
    for famille in familles:
        if famille in disponibles:
            f = QFont(famille, APP_FONT_SIZE)
            f.setStyleStrategy(QFont.PreferAntialias)
            return f
    return QFont("sans-serif", APP_FONT_SIZE)


def _excepthook(exc_type, exc_value, exc_tb):
    details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Erreur inattendue")
    msg.setText(f"Une erreur est survenue : {exc_value}")
    msg.setDetailedText(details)
    msg.exec_()


def _demande_connexion():
    """Affiche l'ecran de configuration initiale (aucun compte) ou l'ecran
    de connexion. Retourne l'utilisateur connecte ou None."""
    if not auth.has_accounts():
        setup = FirstSetupDialog()
        if setup.exec_() == FirstSetupDialog.Accepted:
            user = setup.user
            auth.save_session(user["id"])
            return user
        return None

    # Session existante : reconnexion automatique du dernier utilisateur.
    user = auth.get_saved_user()
    if user is not None:
        return user

    login = LoginDialog()
    if login.exec_() == LoginDialog.Accepted:
        return login.user
    return None


def main():
    sys.excepthook = _excepthook
    _setup_high_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setFont(_pick_base_font())
    app.setStyleSheet(APP_STYLESHEET)
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    db.init_db()

    # Boucle de session : apres une deconnexion, on revient a l'ecran de
    # connexion au lieu de quitter l'application.
    while True:
        user = _demande_connexion()
        if user is None:
            sys.exit(0)

        window = MainWindow(user)
        window.showMaximized()
        app.exec_()

        # Fenetre fermee : si la session a ete effacee, c'est une
        # deconnexion volontaire -> nouvel ecran de connexion.
        if auth.get_saved_user() is None:
            continue
        sys.exit(0)


if __name__ == "__main__":
    main()
