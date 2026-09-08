from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLabel, QMainWindow, QMessageBox, QPushButton,
                             QWidget, QVBoxLayout, QHBoxLayout,
                             QStackedWidget, QFrame, QScrollArea,
                             QSpacerItem)

from api import api_disponible
from core.config import APP_NAME, ROLE_LABELS, C_GOLD_LIGHT, C_GOLD_PRESSED, C_RED, C_RED_BG, C_INK, C_GRAD_TOP, C_GRAD_BOTTOM
from ui import pages
from ui import motion
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

PAGE_TITRES = {
    "dashboard": "Tableau de bord",
    "stats": "Statistiques",
    "eleves": "Liste des Eleves",
    "caisse": "Gestion Caisse",
    "tarifs": "Tarifs et Scolarite",
    "paiements": "Paiements et Suivi",
    "classes": "Classes",
    "cycles": "Cycles et Annees",
    "notes": "Notes et Bulletins",
    "presences": "Presences",
    "planning": "Emploi du Temps",
    "personnel": "Personnel et RH",
    "programmes": "Matieres et Programmes",
    "parametres": "Parametres Etablissement",
    "comptes": "Gestion des Comptes",
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
        self._failed_pages = set()
        self._current = None
        self.setMinimumSize(960, 600)
        self.setWindowTitle(f"{APP_NAME} - {user['nom_complet']}")
        apply_ui("main.ui", self)

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
        self.lbl_api_status.installEventFilter(self)
        self.btn_logout.clicked.connect(self.logout)
        self._api_checking = False
        self._refresh_api_status()

        self._wire_nav()
        self._wrap_nav_in_scroll()
        self._ajouter_bouton_assistant()
        self._construire_entete()
        self.navigate("dashboard")

    def _construire_entete(self):
        """Barre superieure moderne : fil d'Ariane (titre de section),
        date du jour et chip d'accent or. Placee au-dessus du contenu."""
        colonne = QWidget()
        colonne.setObjectName("pageColonne")
        v = QVBoxLayout(colonne)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        entete = QFrame()
        entete.setObjectName("pageEntete")
        entete.setStyleSheet(
            "QFrame#pageEntete { background: #FDFCFA;"
            " border-bottom: 1px solid #E9E6DE; }")
        h = QHBoxLayout(entete)
        h.setContentsMargins(22, 10, 22, 10)
        h.setSpacing(12)

        titre = QLabel(PAGE_TITRES.get("dashboard", ""))
        titre.setObjectName("lbl_page_titre")
        titre.setStyleSheet(
            f"color: {C_INK}; font-size: 15px; font-weight: 700;")
        h.addWidget(titre)
        h.addStretch(1)

        date_auj = QLabel(_aujourdhui())
        date_auj.setObjectName("lbl_page_date")
        date_auj.setStyleSheet(
            "color: #8B857A; font-size: 12px; font-weight: 500;")
        h.addWidget(date_auj)

        chip = QLabel(APP_NAME.upper())
        chip.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM});"
            " color: #FFFFFF; font-weight: 800; font-size: 10px;"
            " letter-spacing: 1px; padding: 4px 12px; border-radius: 10px;")
        chip.setAlignment(Qt.AlignCenter)
        h.addWidget(chip)

        v.addWidget(entete)
        v.addWidget(self.stackedWidget, 1)

        lay = self.mainLayout
        idx = lay.indexOf(self.stackedWidget)
        lay.removeWidget(self.stackedWidget)
        lay.insertWidget(idx, colonne, 1)

        self.lbl_page_titre = titre
        self._entete = entete

    def _ajouter_bouton_assistant(self):
        """Bouton de l'assistante locale Charo, ajoute programmatiquement a la
        fin de la navigation (le .ui n'est pas modifie : aucun risque pour
        les autres boutons)."""
        from ui.pages.assistant_page import ouvrir_assistant_ia

        btn = QPushButton("Assistant IA")
        btn.setObjectName("btn_nav_assistant")
        btn.setCursor(Qt.PointingHandCursor)
        # PAS checkable : c'est une action (ouvrir la fenetre), pas une page.
        # Un bouton checkable restait coche apres le clic et affichait le
        # style ":checked" du theme (bordure noire epaisse).
        btn.setToolTip("Ouvre l'assistante Charo.")
        btn.setStyleSheet(
            "QPushButton { color: #EDF0F7; text-align: left; padding: 8px 16px;"
            " border: none; margin: 2px 12px; border-radius: 10px;"
            " font-size: 13px; font-weight: 600; background: transparent; }"
            "QPushButton:hover { background-color: rgba(255,255,255,0.08);"
            " color: #FFFFFF; border-left: 3px solid #EAB43B; }"
            "QPushButton:pressed { background-color: rgba(255,255,255,0.12); }")
        btn.clicked.connect(lambda: ouvrir_assistant_ia(self, self.ctx))
        layi = self.navScroll.widget().layout()
        layi.insertWidget(max(layi.count() - 1, 0), btn)
        self.btn_nav_assistant = btn
        motion.hover_lift([btn])

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

    def eventFilter(self, source, event):
        from PyQt5.QtCore import QEvent
        if source is self.lbl_api_status and event.type() == QEvent.MouseButtonPress:
            self._ouvrir_assistant_serveur()
            return True
        return super().eventFilter(source, event)

    def _ouvrir_assistant_serveur(self):
        if not self.ctx.authorizer.can_edit("parametres"):
            QMessageBox.information(
                self, "Connexion multi-postes",
                "Seul le directeur peut modifier la connexion entre "
                "les postes.\n\n"
                "Demandez-lui d'ouvrir l'assistant (badge en bas a droite).")
            return
        from ui.assistant_serveur import ouvrir_assistant
        ouvrir_assistant(self, apres_changement=self._refresh_api_status)

    def _refresh_api_status(self):
        """Badge d'etat serveur, honnete sur la cause :

        - Mode Autonome      : synchronisation desactivee (choix/config)
        - En Ligne           : le serveur de l'ecole repond
        - Serveur Injoignable: synchro activee mais serveur absent
          (etre connecte a Internet ne suffit pas : c'est le serveur
          GS qui est teste, pas le web en general).

        Un clic sur le badge ouvre l'assistant graphique multi-postes.
        """
        from core import network

        def _style(bg, fg):
            return ("padding: 3px 12px; border-radius: 10px; font-weight: 700;"
                    f" font-size: 11px; background-color: {bg}; color: {fg};"
                    " border: 1px solid transparent;")

        self.lbl_api_status.setCursor(Qt.PointingHandCursor)

        if not network.sync_active():
            self.lbl_api_status.setText("Mode Autonome")
            self.lbl_api_status.setStyleSheet(_style(C_GOLD_LIGHT, C_GOLD_PRESSED))
            self.lbl_api_status.setToolTip(
                "Synchronisation entre postes desactivee.\n"
                "Les donnees restent enregistrees sur ce poste.\n"
                "Cliquez ici pour ouvrir l'assistant et activer la\n"
                "connexion entre les ordinateurs de l'ecole.")
            return

        if self._api_checking:
            return
        self._api_checking = True
        self.lbl_api_status.setText("Connexion...")
        self.lbl_api_status.setStyleSheet(_style(C_GOLD_LIGHT, C_GOLD_PRESSED))

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
                    _style("#E4F6E9", "#1B7A3D"))
                self.lbl_api_status.setToolTip(
                    "Connecte au serveur de l'ecole.\n"
                    "Les modifications du directeur se propagent aux autres\n"
                    "postes (structure rapatriee automatiquement).")
                motion.bounce_pulse(self.lbl_api_status, fois=2, duree=220)
            else:
                self.lbl_api_status.setText("Serveur Injoignable")
                self.lbl_api_status.setStyleSheet(_style(C_RED_BG, C_RED))
                self.lbl_api_status.setToolTip(
                    "Le logiciel ne rejoint pas le serveur de l'ecole\n"
                    "(GS_API_URL, par defaut http://127.0.0.1:8000).\n"
                    "Verifiez que le serveur est demarre :\n"
                    "une connexion Internet normale ne suffit pas.")

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

        motion.hover_lift([getattr(self, n) for n in NAV_PAGES if
                           getattr(self, n).isVisible()])

    def _apply_cartoon_shadows(self):
        """Deprecated (supprimee pour le theme moderne). Conservee pour
        compatibilite si un ancien code la reference."""
        return

    def _get_page(self, page_name):
        # Une page dont le chargement a echoue est retentee a chaque
        # navigation : l'erreur etait souvent transitoire (ex: donnees en
        # cours de creation) et il ne faut pas la garder en cache pour toujours.
        if page_name in self._failed_pages:
            old = self._pages.pop(page_name, None)
            self._failed_pages.discard(page_name)
            if old is not None:
                self.stackedWidget.removeWidget(old)
                old.deleteLater()
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
            self._failed_pages.add(page_name)
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
            label = QLabel(f"Erreur de chargement ({page_name}) : {exc}\n\n"
                           "Retournez dans cette section pour reessayer.")
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
        if hasattr(self, "lbl_page_titre"):
            self.lbl_page_titre.setText(PAGE_TITRES.get(
                page_name, PAGE_TITRES.get("dashboard", "")))
        if page_name == "dashboard":
            self._refresh_api_status()
        for btn_name, page in NAV_PAGES.items():
            btn = getattr(self, btn_name)
            if page == page_name and btn.isVisible():
                btn.setChecked(True)
            elif btn.isVisible():
                btn.setChecked(False)
        motion.fade_in(widget, duree=240)
        self.statusBar().showMessage(f"Section active : {page_name}", 1600)


def _aujourdhui():
    """Date du jour au format « lundi 9 septembre 2026 » (sans accents,
    en cohérence avec le reste de l'interface)."""
    import datetime
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi",
             "Samedi", "Dimanche"]
    mois = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
            "aout", "septembre", "octobre", "novembre", "decembre"]
    d = datetime.date.today()
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"
