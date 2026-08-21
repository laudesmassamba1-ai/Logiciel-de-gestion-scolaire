from PyQt5.QtCore import Qt, QPropertyAnimation
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QLabel, QMainWindow, QMessageBox, QWidget,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                             QVBoxLayout, QStackedWidget, QFrame, QScrollArea,
                             QSpacerItem)

from api import api_disponible
from core.config import APP_NAME, ROLE_LABELS, C_BG, C_GOLD_LIGHT, C_GOLD_PRESSED, C_BLUE_LIGHT, C_BLUE, C_RED
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

# Titres de section de la sidebar : visibles seulement si au moins une
# page de la section est accessible au role courant.
NAV_SECTIONS = {
    "lbl_section_general": ["dashboard", "stats"],
    "lbl_section_scolarite": ["eleves", "classes", "cycles", "notes",
                               "presences", "planning", "programmes"],
    "lbl_section_finances": ["caisse", "tarifs", "paiements"],
    "lbl_section_administration": ["personnel", "parametres", "comptes"],
}

DASHBOARD_BUILDERS = {
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
    def __init__(self, user, on_logout=None):

        super().__init__()
        self.user = user
        self.on_logout = on_logout
        self.ctx = pages.PageContext(user, self.navigate)
        self._pages = {}
        self._current = None
        self._fade_anim = None
        self._fade_target = None
        self.setMinimumSize(960, 600)
        self.setWindowTitle(f"{APP_NAME} - {user['nom_complet']}")
        apply_ui("main.ui", self)
        self.setStyleSheet(f"QMainWindow {{ background-color: {C_BG}; }}")

        self.lbl_user_name.setText(user["nom_complet"])
        self.lbl_user_role.setText(ROLE_LABELS.get(user["role"], user["role"]))
        self.statusBar().showMessage(
            f"Connecte comme {user['nom_complet']} ({ROLE_LABELS.get(user['role'], user['role'])})",
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
        self._wrap_nav_in_scroll()
        self.navigate("dashboard")

    def _wrap_nav_in_scroll(self):
        """Place les boutons de navigation dans une zone defilable.

        Sans cela, sur un petit ecran le layout ecrase les widgets du bas
        (carte utilisateur aplatie, textes coupes)."""
        lay = self.verticalLayout
        skip = {"lbl_logo", "lbl_logo_subtitle", "userBox"}

        container = QWidget()
        container.setObjectName("navContainer")
        container.setStyleSheet("background: transparent;")
        nav_lay = QVBoxLayout(container)
        nav_lay.setContentsMargins(0, 4, 0, 4)
        nav_lay.setSpacing(2)

        moved = []
        spacer = None
        for i in range(lay.count()):
            item = lay.itemAt(i)
            widget = item.widget()
            if widget is not None:
                if widget.objectName() in skip:
                    continue
                moved.append(widget)
            elif isinstance(item, QSpacerItem):
                spacer = item
        for widget in moved:
            lay.removeWidget(widget)
            nav_lay.addWidget(widget)
        nav_lay.addStretch(1)
        if spacer is not None:
            lay.removeItem(spacer)

        scroll = QScrollArea()
        scroll.setObjectName("navScroll")
        self.navScroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setAutoFillBackground(False)
        scroll.setWidget(container)

        lay.insertWidget(2, scroll, 1)
        self.userBox.setMinimumHeight(96)

    def _refresh_api_status(self):
        if self._api_checking:
            return
        self._api_checking = True
        self.lbl_api_status.setText("Mode Local")
        self.lbl_api_status.setStyleSheet(
            "padding: 2px 10px; border-radius: 4px; font-weight: bold;"
            f" background-color: {C_GOLD_LIGHT}; color: {C_GOLD_PRESSED};")

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
                    f" background-color: {C_BLUE_LIGHT}; color: {C_BLUE};")

        run_async(_check, _on)

    def logout(self):

        reponse = QMessageBox.question(
            self, "Deconnexion", "Voulez-vous vraiment vous deconnecter ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reponse == QMessageBox.Yes:
            from services.auth import AuthService
            AuthService().clear_session()
            self.close()
            if self.on_logout:
                self.on_logout()

    def _wire_nav(self):

        for btn_name, page_name in NAV_PAGES.items():
            btn = getattr(self, btn_name)
            if self.ctx.authorizer.allowed(page_name):
                btn.setVisible(True)
                btn.clicked.connect(lambda _=False, p=page_name: self.navigate(p))
            else:
                btn.setVisible(False)
                btn.setChecked(False)

        for lbl_name, pages_in_section in NAV_SECTIONS.items():
            lbl = getattr(self, lbl_name, None)
            if lbl is None:
                continue
            visible = any(self.ctx.authorizer.allowed(p) for p in pages_in_section)
            lbl.setVisible(visible)

        self._apply_cartoon_shadows()

    def _apply_cartoon_shadows(self):
        """Ombres dures style cartoon : decalage net, sans flou.
        NB : jamais d'effet graphique sur la carte utilisateur (userBox) :
        le rendu en pixmap de QGraphicsDropShadowEffect aplatit/floute
        le texte qu'elle contient."""
        for btn_name in NAV_PAGES:
            btn = getattr(self, btn_name)
            effect = QGraphicsDropShadowEffect(btn)
            effect.setBlurRadius(0)
            effect.setOffset(3, 3)
            effect.setColor(QColor(17, 17, 17, 55))
            btn.setGraphicsEffect(effect)

    def _get_page(self, page_name):
        widget = self._pages.get(page_name)
        if widget is not None:
            return widget
        if page_name == "dashboard":
            builder = DASHBOARD_BUILDERS.get(self.user["role"], pages.dashboard_gestionnaire)
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
            old = widget.layout()
            if old is not None:
                while old.count():
                    item = old.takeAt(0)
                    w = item.widget()
                    if w:
                        w.setParent(None)
                old.setParent(None)
            lay = QVBoxLayout(widget)
            label = QLabel(f"Erreur de chargement ({page_name}) : {exc}")
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {C_RED}; padding: 20px;")
            lay.addWidget(label)
        self.stackedWidget.addWidget(widget)
        self._pages[page_name] = widget
        return widget

    def navigate(self, page_name):

        # Garde d'acces : un role non autorise ne peut jamais afficher
        # la page, meme par appel programmatique.
        if not self.ctx.authorizer.allowed(page_name):
            QMessageBox.warning(
                self, "Acces refuse",
                "Votre profil ne permet pas d'acceder a cette section.")
            page_name = "dashboard"
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
        self.statusBar().showMessage(f"Section active : {page_name}", 1600)

    def _fade_in(self, widget):
        if self._fade_anim is not None:
            self._fade_anim.stop()
            prev = self._fade_target
            if prev:
                prev.setGraphicsEffect(None)
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
        self._fade_anim = anim
        self._fade_target = widget
        anim.start()
