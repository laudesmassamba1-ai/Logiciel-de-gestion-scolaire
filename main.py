import os
import sys
import threading
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from core.config import APP_NAME, APP_STYLESHEET, APP_FONT_FAMILY, APP_FONT_FALLBACK, APP_FONT_SIZE, SYNC_ACTIVE, SERVEUR_AUTO
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
            if user is not None:
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

    # Auto-demarrage du serveur si ce poste est l'hote et que l'option
    # « Demarrer le serveur en meme temps que l'application » est active
    # (serveur_auto=True dans sync.json). Tout se passe en arriere-plan :
    # la fenetre apparait immediatement, la verrification du serveur et
    # l'attente qu'il reponde ne bloquent plus le lancement (avant, le
    # demarrage pouvait rester fige ~15 s, comme si l'application ne
    # repondait pas).
    if SERVEUR_AUTO:
        from services import serveur_local as sl
        from core import network as _network

        def _auto_demarrer():
            try:
                ok, _ = sl.demarrer_si_auto()
                if ok:
                    _network.set_sync_active(True)
                    _network.set_online()
            except Exception as exc:
                print("Serveur automatique : echec", exc)

        threading.Thread(target=_auto_demarrer, daemon=True).start()

    # Thread de synchronisation (push de la file d'attente + pull de la
    # structure modifiee par le directeur). Demarre des que la sync est
    # active, ou des que le poste doit hoster le serveur : il idlera
    # tant que le reseau n'est pas joignable.
    if SYNC_ACTIVE or SERVEUR_AUTO:
        from api.sync_worker import SyncWorker
        _sync_worker = SyncWorker()

        def _stop_sync_worker():
            _sync_worker.requestInterruption()
            _sync_worker.wait(3000)
        app.aboutToQuit.connect(_stop_sync_worker)
        _sync_worker.start()

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
