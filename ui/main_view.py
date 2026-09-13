from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QLabel, QMainWindow, QMessageBox, QPushButton,
                             QShortcut, QWidget, QVBoxLayout, QHBoxLayout,
                             QStackedWidget, QFrame, QScrollArea,
                             QSpacerItem, QLineEdit, QSizePolicy)

from api import api_disponible
from core.config import (
    APP_NAME, ROLE_LABELS, C_GOLD_LIGHT, C_GOLD_PRESSED, C_RED,
    C_RED_BG, C_INK, C_GRAD_TOP, C_GRAD_BOTTOM,
    STYLE_ENTETE, STYLE_ENTETE_TITRE, STYLE_ENTETE_DATE,
    STYLE_RECHERCHE, STYLE_CHIP_APP, STYLE_NAV_ASSISTANT,
    STYLE_BADGE_API,
)
from ui import pages
from ui import motion
from ui.decor import creer_avatar
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

        self._poser_icones_nav()

        self.lbl_user_name.setText(user["nom_complet"])
        self.lbl_user_role.setText(ROLE_LABELS.get(user["role"], user["role"]))
        self.statusBar().hide()
        self._inserer_avatar()
        self.lbl_api_status = QLabel()
        self.lbl_api_status.setStyleSheet(
            STYLE_BADGE_API + " background-color: #FEF3C7; color: #A67B0A;")
        self.lbl_api_status.installEventFilter(self)
        self.btn_logout.clicked.connect(self.logout)
        self._api_checking = False
        self._refresh_api_status()

        self._wire_nav()
        self._wrap_nav_in_scroll()
        self._ajouter_bouton_assistant()
        self._construire_entete()
        self._installer_palette()
        self.navigate("dashboard")

    def _inserer_avatar(self):
        """Avatar circulaire (initiales) a cote du nom, en haut de la
        carte utilisateur de la sidebar."""
        avatar = creer_avatar(self.user["nom_complet"], 36)
        cartouche = QWidget()
        cartouche.setObjectName("userCartouche")
        cartouche.setStyleSheet("background: transparent;")
        ch = QHBoxLayout(cartouche)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(10)
        ch.addWidget(avatar)
        infos = QVBoxLayout()
        infos.setContentsMargins(0, 0, 0, 0)
        infos.setSpacing(0)
        infos.addWidget(self.lbl_user_name)
        infos.addWidget(self.lbl_user_role)
        ch.addLayout(infos, 1)
        ch.addStretch(0)

        lay = self.userBoxLayout
        lay.removeWidget(self.lbl_user_name)
        lay.removeWidget(self.lbl_user_role)
        lay.insertWidget(0, cartouche)
        self.userBox.setMinimumHeight(78)

    def _poser_icones_nav(self):
        """Icônes qtawesome (FA5) sur les boutons de la sidebar."""
        try:
            import qtawesome as qta
        except ImportError:
            return
        icones = {
            "btn_nav_dashboard": "fa5s.th-large",
            "btn_nav_stats": "fa5s.chart-bar",
            "btn_nav_eleves": "fa5s.user-graduate",
            "btn_nav_caisse": "fa5s.money-bill-alt",
            "btn_nav_tarifs": "fa5s.tags",
            "btn_nav_paiements": "fa5s.hand-holding-usd",
            "btn_nav_classes": "fa5s.school",
            "btn_nav_cycles": "fa5s.history",
            "btn_nav_notes": "fa5s.clipboard-list",
            "btn_nav_presences": "fa5s.calendar-check",
            "btn_nav_planning": "fa5s.calendar-alt",
            "btn_nav_personnel": "fa5s.users",
            "btn_nav_programmes": "fa5s.book",
            "btn_nav_parametres": "fa5s.cog",
            "btn_nav_comptes": "fa5s.user-shield",
        }
        for nom_btn, icone in icones.items():
            btn = getattr(self, nom_btn, None)
            if btn is None:
                continue
            try:
                btn.setIcon(qta.icon(icone, color="#C8960C"))
                btn.setIconSize(QSize(16, 16))
            except Exception:
                continue

    def _installer_palette(self):
        """Palette de commandes (Ctrl+K) : chercher une section et y naviguer,
        ou lancer une action (assistante, deconnexion). Style Spotlight."""
        from ui.palette import Palette

        self._palette = None
        self._palette_raccourci = QShortcut(QKeySequence("Ctrl+K"), self)
        self._palette_raccourci.setContext(Qt.WindowShortcut)
        self._palette_raccourci.activated.connect(self._ouvrir_palette)

        def _sur_choix(cle):
            if cle == "action:assistant":
                from ui.pages.assistant_page import ouvrir_assistant_ia
                ouvrir_assistant_ia(self, self.ctx)
                return
            if cle == "action:logout":
                self.logout()
                return
            self.navigate(cle)

        self._sur_choix_palette = _sur_choix

        def _construire_entrees():
            entrees = []
            for btn_name, page_name in NAV_PAGES.items():
                if self.ctx.authorizer.allowed(page_name):
                    entrees.append((PAGE_TITRES.get(page_name, page_name),
                                    _conseil_page(page_name), page_name))
            entrees.append(("Assistant IA", "Charo, l'assistante locale",
                            "action:assistant"))
            entrees.append(("Deconnexion", "Quitter cette session",
                            "action:logout"))
            return entrees

        self._entrees_palette = _construire_entrees

    def _ouvrir_palette(self, filtre=""):
        from ui.palette import Palette
        if self._palette is None:
            self._palette = Palette(self)
            self._palette.choisi.connect(self._sur_choix_palette)
        self._palette.ouvrir(self._entrees_palette(), filtre=filtre)

    def _construire_entete(self):
        """Barre superieure moderne : fil d'Ariane (titre de section), champ
        de recherche, date et badge serveur. Placee au-dessus du contenu."""
        colonne = QWidget()
        colonne.setObjectName("pageColonne")
        v = QVBoxLayout(colonne)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        entete = QFrame()
        entete.setObjectName("pageEntete")
        entete.setStyleSheet(STYLE_ENTETE)
        h = QHBoxLayout(entete)
        h.setContentsMargins(20, 8, 20, 8)
        h.setSpacing(12)

        titre = QLabel(_section_label("dashboard"))
        titre.setObjectName("lbl_page_titre")
        titre.setStyleSheet(STYLE_ENTETE_TITRE)
        titre.setMinimumWidth(120)
        h.addWidget(titre)
        h.addStretch(1)

        date_auj = QLabel(_aujourdhui())
        date_auj.setObjectName("lbl_page_date")
        date_auj.setStyleSheet(STYLE_ENTETE_DATE)
        date_auj.setMinimumWidth(170)
        h.addWidget(date_auj)

        recherche = QLineEdit()
        recherche.setObjectName("recherche_entete")
        recherche.setPlaceholderText("Rechercher une section (Ctrl+K)")
        recherche.setClearButtonEnabled(True)
        # Largeur compressible (jamais figee) : sur petit ecran la barre
        # du haut se replie au lieu de pousser le titre ou le badge API
        # hors de l'ecran.
        recherche.setMinimumWidth(180)
        recherche.setMaximumWidth(300)
        recherche.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        recherche.setStyleSheet(STYLE_RECHERCHE)
        recherche.returnPressed.connect(
            lambda: self._ouvrir_palette(recherche.text().strip()))
        self.recherche_entete = recherche
        recherche.installEventFilter(self)
        h.addWidget(recherche)

        h.addWidget(self.lbl_api_status)

        chip = QLabel(APP_NAME.upper())
        chip.setStyleSheet(STYLE_CHIP_APP)
        chip.setAlignment(Qt.AlignCenter)
        h.addWidget(chip)

        v.addWidget(entete)
        v.addWidget(self.stackedWidget, 1)

        lay = self.mainLayout
        idx = lay.indexOf(self.stackedWidget)
        lay.removeWidget(self.stackedWidget)
        lay.insertWidget(idx, colonne, 1)
        self._colonne = colonne

        self.lbl_page_titre = titre
        self._entete = entete
        self._enrouler_splitter()

    def _enrouler_splitter(self):
        """Cree le separateur entre la sidebar et le contenu : la largeur de
        la navigation devient reglable a la souris dans toute l'application."""
        from PyQt5.QtWidgets import QSplitter
        lay = self.mainLayout
        lay.removeWidget(self.sidebar)
        lay.removeWidget(self._colonne)
        split = QSplitter(Qt.Horizontal)
        split.setObjectName("mainSplit")
        split.setHandleWidth(6)
        split.setChildrenCollapsible(False)
        split.addWidget(self.sidebar)
        split.addWidget(self._colonne)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([208, max(1, self.width() - 208)])
        lay.insertWidget(0, split, 1)
        self.mainSplit = split

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
        btn.setStyleSheet(STYLE_NAV_ASSISTANT)
        btn.clicked.connect(lambda: ouvrir_assistant_ia(self, self.ctx))
        layi = self.navScroll.widget().layout()
        layi.insertWidget(layi.count(), btn)
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
        container.setMinimumSize(0, 0)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
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
            # Largeur : politique "Ignored" -> le layout ignore le
            # minimumSizeHint du bouton le plus long et etire chaque
            # entree a la largeur du menu. Sans cela, le bouton le plus
            # long (ex. « Matieres & Programmes ») force le conteneur a
            # depasser la sidebar et a deborder sur le contenu.
            widget.setSizePolicy(
                QSizePolicy.Ignored, widget.sizePolicy().verticalPolicy())
            widget.setMinimumWidth(0)
            nav_lay.addWidget(widget)
        # PAS de addStretch : le conteneur doit garder sa hauteur naturelle.
        # Avec un etirement, Qt le force a remplir toute la hauteur et ses
        # boutons du bas (Programmes, Comptes, Parametres...) a raient sur
        # la carte utilisateur fixee sous le menu (chevauchement visible).
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
        self.userBox.setMinimumHeight(78)

    def eventFilter(self, source, event):
        from PyQt5.QtCore import QEvent
        if event.type() != QEvent.MouseButtonPress:
            return super().eventFilter(source, event)
        if source is self.lbl_api_status:
            self._ouvrir_assistant_serveur()
            return True
        if getattr(self, "recherche_entete", None) is source:
            self._ouvrir_palette(self.recherche_entete.text().strip())
            self.recherche_entete.clear()
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
            return (STYLE_BADGE_API
                    + f" background-color: {bg}; color: {fg};")

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

        from ui.pages.helpers import confirmer
        if confirmer(self, "Voulez-vous vraiment vous deconnecter ?",
                     "Deconnexion"):
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
            # Reutiliser le layout existant (jamais en recrer un) : en creer
            # un nouveau alors que l'ancien n'est pas encore detruit declenche
            # le warning « QLayout already has a layout » de Qt et fait flotter
            # le message d'erreur.
            old = widget.layout()
            if old is not None:
                while old.count():
                    item = old.takeAt(0)
                    w = item.widget()
                    if w:
                        w.setParent(None)
            else:
                old = QVBoxLayout(widget)
            label = QLabel(f"Erreur de chargement ({page_name}) : {exc}\n\n"
                           "Retournez dans cette section pour reessayer.")
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {C_RED}; padding: 20px;")
            old.addWidget(label)
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
            self.lbl_page_titre.setText(_section_label(page_name))
        if page_name == "dashboard":
            self._refresh_api_status()
        for btn_name, page in NAV_PAGES.items():
            btn = getattr(self, btn_name)
            if page == page_name and btn.isVisible():
                btn.setChecked(True)
            elif btn.isVisible():
                btn.setChecked(False)
        motion.fade_in(widget, duree=240)


def _section_label(page_name):
    """Nom de section affiche dans la barre du haut (fil d'ariane).

    Le titre complet de la page est deja porte par chaque page elle-meme ;
    la barre superieure ne repete donc que la section pour eviter le
    doublon « sans sens ».
    """
    noms = {
        "lbl_section_general": "Vue d'ensemble",
        "lbl_section_scolarite": "Scolarite",
        "lbl_section_finances": "Finances",
        "lbl_section_administration": "Administration",
    }
    for lbl, pages_in in NAV_SECTIONS.items():
        if page_name in pages_in:
            return noms.get(lbl, lbl)
    return "Accueil"


def _conseil_page(page_name):
    """Sous-titre court d'une page, affiche dans la palette de commandes."""
    conseils = {
        "dashboard": "Vue d'ensemble",
        "stats": "Chiffres et tendances",
        "eleves": "Scolarite · dossiers",
        "caisse": "Finances · encaissements",
        "tarifs": "Finances · scolarite",
        "paiements": "Finances · suivi des eleves",
        "classes": "Scolarite · effectifs",
        "cycles": "Organisation pedagogique",
        "notes": "Evaluation · bulletins",
        "presences": "Assiduite",
        "planning": "Emploi du temps",
        "personnel": "Ressources humaines",
        "programmes": "Matieres et programmes",
        "parametres": "Configuration et sauvegardes",
        "comptes": "Utilisateurs et roles",
    }
    return conseils.get(page_name, "")


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
