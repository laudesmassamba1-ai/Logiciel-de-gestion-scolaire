import os
import sys
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication, QMessageBox

from core.config import APP_NAME, APP_STYLESHEET, APP_FONT_FAMILY, APP_FONT_FALLBACK, APP_FONT_SIZE
from database import db
from ui.login_view import LoginDialog
from ui.main_view import MainWindow


def _setup_high_dpi():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def _pick_base_font() -> QFont:
    familles = list(APP_FONT_FALLBACK)
    if APP_FONT_FAMILY not in familles:
        familles.insert(0, APP_FONT_FAMILY)
    disponibles = set(QFontDatabase().families())
    for famille in familles:
        if famille in disponibles:
            return QFont(famille, APP_FONT_SIZE)
    return QFont("sans-serif", APP_FONT_SIZE)


def _excepthook(exc_type, exc_value, exc_tb):
    details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Erreur inattendue")
    msg.setText(f"Une erreur est survenue : {exc_value}")
    msg.setDetailedText(details)
    msg.exec_()

def main():
    sys.excepthook = _excepthook
    _setup_high_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setFont(_pick_base_font())
    app.setStyleSheet(APP_STYLESHEET)

    db.init_db()


    login = LoginDialog()
    if login.exec_() == LoginDialog.Accepted:

        window = MainWindow(login.user)
        window.show()
        sys.exit(app.exec_())
    sys.exit(0)


if __name__ == "__main__":
    main()
