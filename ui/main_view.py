from PyQt5.QtCore import QPropertyAnimation
from PyQt5.QtWidgets import (QLabel, QMainWindow, QMessageBox, QWidget,
                             QGraphicsOpacityEffect, QVBoxLayout)

from api import api_disponible
from core.config import APP_NAME, ROLE_LABELS
from ui import pages
from ui.loader import apply_ui
from ui.workers import run_async


NAV_PAGES = {
    "btn_nav_dashboard": "dashboard",
    "btn_nav_stats": "stats",
    "btn_nav_eleves": "eleves",
    "btn_nav_caisse": "caisse",
    "btn_nav_tarifs": "tarifs",
    "btn_nav_paiements": "paiements",
    "btn_nav_classes": "classes",
    "btn_nav_cycles": "cycles",
    "btn_nav_notes": "notes",
    "btn_nav_presences": "presences",
    "btn_nav_planning": "planning",
    "btn_nav_personnel": "personnel",
    "btn_nav_programmes": "programmes",
    "btn_nav_parametres": "parametres",
    "btn_nav_comptes": "comptes",
}

DASHBOARD_BUILDERS = {
    "admin": pages.dashboard_admin,
    "directeur": pages.dashboard_directeur,
    "gestionnaire": pages.dashboard_gestionnaire,
}

BUILDERS = {
    "stats": pages.statistiques,
    "eleves": pages.eleves,
    "caisse": pages.caisse,
    "tarifs": pages.tarifs,
    "paiements": pages.paiements,
    "classes": pages.classes,
    "cycles": pages.cycles_annees,
    "notes": pages.notes,
    "presences": pages.presences,
    "planning": pages.planning,
    "personnel": pages.personnel,
    "programmes": pages.programmes,
    "parametres": pages.parametres,
    "comptes": pages.comptes,
}


class MainWindow(QMainWindow):
    def __init__(self, user):

        super().__init__()
        self.user = user
        self.ctx = pages.PageContext(user, self.navigate)
        self._pages = {}
        self._current = None
        self.setWindowTitle(f"{APP_NAME} - {user['nom_complet']}")
        self.showMaximized()
        self.setStyleSheet("""
            QMainWindow { background: #f8fafc; }
            QWidget { color: #0f172a; }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                border: none;
                background-color: #047857;
                color: white;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:pressed { background-color: #065f46; }
            QToolButton, QPushButton { border-radius: 8px; }
            QToolButton:checked { background: #d1fae5; border: 1px solid #a7f3d0; }
            QLabel { color: #334155; }
            QLineEdit, QComboBox {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px;
                background-color: #ffffff;
                color: #0f172a;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #047857;
                background-color: #ffffff;
            }
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                gridline-color: #e2e8f0;
                background-color: #ffffff;
            }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section { background-color: #f1f5f9; border: none; padding: 8px; font-weight: bold; color: #334155; }
        """)
        apply_ui("main.ui", self)

        self.lbl_user_name.setText(user["nom_complet"])
        self.lbl_user_role.setText(ROLE_LABELS.get(user["role"], user["role"]))
        self.statusBar().showMessage(
            f"Connecté comme {user['nom_complet']} ({ROLE_LABELS.get(user['role'], user['role'])})",
            2500,
        )
        self.lbl_api_status = QLabel()
        self.lbl_api_status.setStyleSheet(
            "padding: 2px 10px; border-radius: 4px; font-weight: bold;")
        self.statusBar().addPermanentWidget(self.lbl_api_status)
        self.btn_logout.clicked.connect(self.logout)
        self._api_checking = False
        self._refresh_api_status()


        self._wire_nav()
        default = "dashboard" if user["role"] in {"admin", "directeur", "gestionnaire"} else "comptes"
        self.navigate(default)

    def _refresh_api_status(self):
        if self._api_checking:
            return
        self._api_checking = True
        self.lbl_api_status.setText("Mode Local")
        self.lbl_api_status.setStyleSheet(
            "padding: 2px 10px; border-radius: 4px; font-weight: bold;"
            " background-color: #fef9c3; color: #854d0e;")

        def _check():
            try:
                return api_disponible(force=True)
            except Exception:
                return False

        def _on(result):
            self._api_checking = False
            en_ligne = bool(result) and not isinstance(result, Exception)
            if en_ligne:
                self.lbl_api_status.setText("En Ligne")
                self.lbl_api_status.setStyleSheet(
                    "padding: 2px 10px; border-radius: 4px; font-weight: bold;"
                    " background-color: #dcfce7; color: #166534;")

        run_async(_check, _on)

    def logout(self):

        if QMessageBox.question(self, "Déconnexion", "Voulez-vous vraiment vous déconnecter ?") == QMessageBox.Yes:
            self.close()

    def _wire_nav(self):

        for btn_name, page_name in NAV_PAGES.items():
            btn = getattr(self, btn_name)
            if self.ctx.authorizer.allowed(page_name):
                btn.setVisible(True)
                btn.clicked.connect(lambda _=False, p=page_name: self.navigate(p))
            else:
                btn.setVisible(False)

    def _get_page(self, page_name):

        widget = self._pages.get(page_name)
        if widget is not None:
            return widget
        if page_name == "dashboard":
            builder = DASHBOARD_BUILDERS.get(self.user["role"], pages.dashboard_admin)
        else:
            builder = BUILDERS.get(page_name)
        if builder is None:
            return None
        widget = QWidget()
        widget.setObjectName(f"page_{page_name}")
        try:
            builder(widget, self.ctx)
        except Exception as exc:
            from PyQt5.QtWidgets import QLabel, QVBoxLayout
            lay = QVBoxLayout(widget)
            label = QLabel(f"Erreur de chargement ({page_name}) : {exc}")
            label.setWordWrap(True)
            label.setStyleSheet("color: #dc2626; padding: 20px;")
            lay.addWidget(label)
        self.stackedWidget.addWidget(widget)
        self._pages[page_name] = widget
        return widget

    def navigate(self, page_name):

        widget = self._get_page(page_name)
        if widget is None:
            return
        self.stackedWidget.setCurrentWidget(widget)
        refresh = getattr(widget, "refresh", None)
        if refresh:
            refresh()
        self._current = page_name
        if page_name == "dashboard":
            self._refresh_api_status()
        for btn_name, page in NAV_PAGES.items():
            btn = getattr(self, btn_name)
            if page == page_name and btn.isVisible():
                btn.setChecked(True)
            elif btn.isVisible():
                btn.setChecked(False)
        self._fade_in(widget)
        self.statusBar().showMessage(f"Page active : {page_name}", 1600)

    def _fade_in(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._fade_anim = anim
        anim.start()
