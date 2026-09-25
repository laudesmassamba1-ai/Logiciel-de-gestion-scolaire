import os
from PyQt5.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence, QIcon
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QShortcut, QSystemTrayIcon, QWidget,
                             QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame,
                             QScrollArea, QSpacerItem, QLineEdit, QSizePolicy)

from api import api_disponible
from core.config import (
    APP_NAME, ROLE_LABELS, C_RED,
    C_RED_BG, C_GREEN, C_GREEN_BG, C_WARN_BG, C_WARN_TEXT, C_BG,
    C_SIDEBAR_TEXT, C_PRIMARY_LIGHT, C_PRIMARY_PRESSED, T_SIDEBAR_LARGEUR,
    STYLE_ENTETE, STYLE_ENTETE_TITRE, STYLE_ENTETE_DATE,
    STYLE_RECHERCHE, STYLE_CHIP_APP, STYLE_NAV_ASSISTANT,
    STYLE_BADGE_API,
)
from ui import pages
from ui import motion
from resources import design_tokens
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
    "btn_nav_bloc_notes": "bloc_notes",
    "btn_nav_calendrier": "calendrier",
    "btn_nav_documents": "documents",
    "btn_nav_reseau": "reseau",
    "btn_nav_rapports": "rapports",
}

# Titres de section de la sidebar : visibles seulement si au moins une
# page de la section est accessible au role courant.
NAV_SECTIONS = {
    "lbl_section_general": ["dashboard", "stats"],
    "lbl_section_scolarite": ["eleves", "classes", "cycles", "notes",
                               "presences", "planning", "programmes"],
    "lbl_section_finances": ["caisse", "tarifs", "paiements"],
    "lbl_section_administration": ["personnel", "parametres", "comptes"],
    "lbl_section_outils": ["bloc_notes", "calendrier", "documents", "reseau",
                           "rapports"],
}

# --- Configuration « pages » du theme personnalise ---------------------
# Le configurateur graphique peut reordonner la sidebar et masquer des pages :
# `pages.ordre` = liste complete des pages dans l'ordre voulu,
# `pages.masquees` = pages a retirer de la navigation.
_PAGES_THEME = getattr(design_tokens, "THEME_BRUT", {}) or {}
if isinstance(_PAGES_THEME.get("pages"), dict) and _PAGES_THEME["pages"]:
    _pages_cfg = _PAGES_THEME["pages"]
    if isinstance(_pages_cfg.get("ordre"), list) and _pages_cfg["ordre"]:
        _par_nom = {v: k for k, v in NAV_PAGES.items()}
        _nav_reordonne = {}
        for _nom in _pages_cfg["ordre"]:
            if _nom in _par_nom:
                _nav_reordonne[_par_nom[_nom]] = _nom
        for _cle, _nom in NAV_PAGES.items():  # pages non listees : a la fin
            if _nom not in _nav_reordonne.values():
                _nav_reordonne[_cle] = _nom
        NAV_PAGES = _nav_reordonne
    if isinstance(_pages_cfg.get("masquees"), list):
        _masquees = set(_pages_cfg["masquees"])
        NAV_PAGES = {k: v for k, v in NAV_PAGES.items() if v not in _masquees}
    NAV_SECTIONS = {
        lbl: [p for p in pages_in_section if p in NAV_PAGES.values()]
        for lbl, pages_in_section in NAV_SECTIONS.items()
    }

DASHBOARD_BUILDERS = {
    "directeur": pages.dashboard_directeur,
    "gestionnaire": pages.dashboard_gestionnaire,
}

# Icones FA5 par defaut de la sidebar (utilisees par _poser_icones_nav et
# proposees a l'edition dans le configurateur graphique -> Pages & icones).
ICONES_DEFAUTS = {
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
    "btn_nav_bloc_notes": "fa5s.sticky-note",
    "btn_nav_calendrier": "fa5s.solid.calendar-alt",
    "btn_nav_documents": "fa5s.folder-open",
    "btn_nav_reseau": "fa5s.network-wired",
    "btn_nav_rapports": "fa5s.file-pdf",
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
    "bloc_notes": "Bloc Notes",
    "calendrier": "Calendrier",
    "documents": "Espace Documents",
    "reseau": "Reseau des postes",
    "rapports": "Rapports PDF",
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
    "bloc_notes": pages.bloc_notes,
    "calendrier": pages.calendrier,
    "documents": pages.documents,
    "reseau": pages.reseau,
    "rapports": pages.rapports,
}


class MainWindow(QMainWindow):
    """Fenetre principale avec signaux pour mise a jour temps reel."""
    # Signal emis quand une alarme declenche (texte, jour, heure)
    alarme_declenchee = pyqtSignal(str, str, str)

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
        
        # Icone de la fenetre (pour system tray)
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._poser_icones_nav()

        self.lbl_user_name.setText(user["nom_complet"])
        self.lbl_user_role.setText(ROLE_LABELS.get(user["role"], user["role"]))
        self.statusBar().hide()
        self._inserer_avatar()
        self.lbl_api_status = QLabel()
        self.lbl_api_status.setStyleSheet(
            STYLE_BADGE_API + f" background-color: {C_WARN_BG};"
            f" color: {C_WARN_TEXT};")
        self.lbl_api_status.installEventFilter(self)
        self.btn_logout.clicked.connect(self.logout)
        self._api_checking = False
        self._refresh_api_status()

        # Le poste peut rejoindre le serveur de l'ecole tout seul en
        # arriere-plan (sync_worker) : on rafraichit le badge regulierement
        # pour qu'il passe a « En Ligne » sans action de l'utilisateur.
        self._api_timer = QTimer(self)
        self._api_timer.setInterval(8000)
        self._api_timer.timeout.connect(self._refresh_api_status)
        self._api_timer.start()

        # Alarms du calendrier : verification reguliere, chaque alarme ne
        # sonne qu'une seule fois (marquee signalee apres notification).
        self._alarmes_verifiees = []
        self._minuteur_alarmes = QTimer(self)
        self._minuteur_alarmes.setInterval(10000)
        self._minuteur_alarmes.timeout.connect(self._verifier_alarmes)
        self._minuteur_alarmes.start()

        # Verification immediate au demarrage pour rattraper les alarmes
        # ratees pendant que l'app etait fermee
        QTimer.singleShot(2000, self._verifier_alarmes)

        self._wire_nav()
        self._wrap_nav_in_scroll()
        self._ajouter_bouton_assistant()
        self._construire_entete()
        self._installer_palette()

        # Raccourci CACHE « Configurateur graphique » (theme, pages,
        # tailles, couleurs) : outil avance, volontairement non affiche
        # dans l'interface standard.
        self._sc_config_theme = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        self._sc_config_theme.activated.connect(self._ouvrir_configurateur)

        # Page de demarrage : reglage LOCAL au poste (configurateur -> Poste).
        _local_cfg = (getattr(design_tokens, "THEME_BRUT", {}) or {}).get("local") or {}
        _demarrage = _local_cfg.get("page_demarrage") or "dashboard"
        if _demarrage in BUILDERS:
            self.navigate(_demarrage)
        else:
            self.navigate("dashboard")

    def _ouvrir_configurateur(self):
        from ui.pages.configurateur import ConfigurateurTheme
        fenetre = ConfigurateurTheme(self)
        fenetre.exec_()

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
        icones = dict(ICONES_DEFAUTS)
        # Icônes personnalisables (configurateur -> Pages) : surcharge des
        # entrees dont le theme fournit une icone « fa5s.* » valide.
        _icones_theme = (getattr(design_tokens, "THEME_BRUT", {}) or {}).get("icones") or {}
        if isinstance(_icones_theme, dict):
            for _nom_page, _icone in _icones_theme.items():
                if not isinstance(_icone, str) or not _icone.startswith("fa5"):
                    continue
                for _nom_btn, _nom_page_btn in NAV_PAGES.items():
                    if _nom_page_btn == _nom_page:
                        icones[_nom_btn] = _icone
        for nom_btn, icone in icones.items():
            btn = getattr(self, nom_btn, None)
            if btn is None:
                continue
            try:
                btn.setIcon(qta.icon(icone, color=C_SIDEBAR_TEXT))
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
        split.setSizes([T_SIDEBAR_LARGEUR, max(1, self.width() - T_SIDEBAR_LARGEUR)])
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
            self._synchroniser_badge()
            return True
        if getattr(self, "recherche_entete", None) is source:
            self._ouvrir_palette(self.recherche_entete.text().strip())
            self.recherche_entete.clear()
            return True
        return super().eventFilter(source, event)

    def _verifier_alarmes(self):
        from repositories import repos
        from ui import toast
        uid = self.user.get("id", 0)
        nouvelles = []
        for ev in repos.agenda.alarmes_dues(uid):
            if ev["id"] in self._alarmes_verifiees:
                continue
            self._alarmes_verifiees.append(ev["id"])
            repos.agenda.marquer_alarme_signalee(ev["id"])
            nouvelles.append(ev)
        if not nouvelles:
            return
        for ev in nouvelles:
            texte = f"\U0001F514 {ev['titre']}" + (f" ({ev['jour']} {ev['heure'] or ''})" if ev['heure'] else f" ({ev['jour']})")
            # Toast non-bloquant (visible si l'app est au premier plan)
            toast.info(self, texte)
            # Notification systeme (visible meme si l'app est reduite)
            self._notifier_systeme(ev['titre'], ev['jour'], ev['heure'] or "")
            # Afficher la boite de dialogue d'alarme persistante (son en boucle)
            self._afficher_dialogue_alarme(ev)
            # Signal pour mise a jour temps reel (page calendrier)
            self.alarme_declenchee.emit(ev["titre"], ev["jour"], ev["heure"] or "")

    def _afficher_dialogue_alarme(self, evenement):
        """Affiche une dialogue modale d'alarme avec son en boucle jusqu'a action utilisateur."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QCheckBox
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtMultimedia import QSoundEffect
        from PyQt5.QtCore import QUrl
        from core.config import (data_dir, assurer_ressource, C_RED, C_RED_HOVER, C_RED_PRESSED,
                                 C_GREEN, C_GREEN_BG, C_AURORA,
                                 C_TEXT, C_WARNING, C_WARN_BG,
                                 C_WARNING_HOVER, C_WARNING_PRESSED, C_CONTOUR)
        
        dlg = QDialog(self)
        dlg.setWindowTitle("🔔 Alarme - " + evenement['titre'])
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
        dlg.setModal(True)
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(f"""
            QDialog {{ {C_AURORA} }}
            QLabel {{ color: {C_TEXT}; }}
            QPushButton {{ 
                border-radius: 10px; padding: 12px 24px; font-weight: 600; font-size: 13px;
            }}
        """)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Icon + titre
        titre_lbl = QLabel(f"🔔  {evenement['titre']}")
        titre_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C_RED};")
        titre_lbl.setWordWrap(True)
        layout.addWidget(titre_lbl)
        
        # Details
        details = []
        if evenement['jour']:
            details.append(f"📅 {evenement['jour']}")
        if evenement['heure']:
            details.append(f"⏰ {evenement['heure']}")
        if details:
            detail_lbl = QLabel("  •  ".join(details))
            detail_lbl.setStyleSheet(f"font-size: 14px; color: {C_TEXT};")
            layout.addWidget(detail_lbl)
        
        # Checkbox snooze
        cb_snooze = QCheckBox("Reporter de 10 minutes")
        cb_snooze.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        layout.addWidget(cb_snooze)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        btn_arreter = QPushButton("⏹  Arrêter l'alarme")
        btn_arreter.setStyleSheet(f"""
            QPushButton {{ background: {C_RED}; color: white; border: 1px solid {C_CONTOUR}; }}
            QPushButton:hover {{ background: {C_RED_HOVER}; }}
            QPushButton:pressed {{ background: {C_RED_PRESSED}; }}
        """)
        btn_arreter.setMinimumHeight(48)

        btn_snooze = QPushButton("⏸  Snooze (10 min)")
        btn_snooze.setStyleSheet(f"""
            QPushButton {{ background: {C_WARNING}; color: white; border: 1px solid {C_CONTOUR}; }}
            QPushButton:hover {{ background: {C_WARNING_HOVER}; }}
            QPushButton:pressed {{ background: {C_WARNING_PRESSED}; }}
        """)
        btn_snooze.setMinimumHeight(48)
        
        btn_layout.addWidget(btn_snooze)
        btn_layout.addWidget(btn_arreter)
        layout.addLayout(btn_layout)
        
        # Son en boucle
        son_path = assurer_ressource("alarm.wav")
        effect = None
        timer_loop = None
        
        def jouer_son_en_boucle():
            nonlocal effect, timer_loop
            if son_path.exists():
                effect = QSoundEffect(dlg)
                effect.setSource(QUrl.fromLocalFile(str(son_path)))
                effect.setVolume(0.8)
                effect.play()
                # Rejouer toutes les 3 secondes (approx durée son)
                timer_loop = QTimer(dlg)
                timer_loop.setInterval(3000)
                timer_loop.timeout.connect(lambda: effect.play() if effect else None)
                timer_loop.start()
            else:
                # Fallback beep système
                timer_loop = QTimer(dlg)
                timer_loop.setInterval(1500)
                timer_loop.timeout.connect(lambda: QApplication.beep())
                timer_loop.start()
        
        def arreter_son():
            if timer_loop:
                timer_loop.stop()
            if effect:
                effect.stop()
        
        def on_arreter():
            arreter_son()
            # Marquer l'alarme comme traitée si pas snooze
            if not cb_snooze.isChecked():
                from repositories import repos
                repos.agenda.marquer_alarme_signalee(evenement["id"])
            dlg.accept()
        
        def on_snooze():
            arreter_son()
            from repositories import repos
            # Reporter l'événement de 10 minutes
            from datetime import datetime, timedelta
            try:
                dt_str = f"{evenement['jour']} {evenement['heure'] or '00:00'}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                nouveau_dt = dt + timedelta(minutes=10)
                repos.agenda.modifier(evenement["id"], evenement['titre'],
                                    nouveau_dt.strftime("%Y-%m-%d"),
                                    nouveau_dt.strftime("%H:%M"),
                                    evenement.get('note', ''), 1)
            except Exception:
                pass
            dlg.accept()
        
        btn_arreter.clicked.connect(on_arreter)
        btn_snooze.clicked.connect(on_snooze)
        
        # Démarrer le son immédiatement
        jouer_son_en_boucle()
        
        # Fermer proprement
        def on_reject():
            arreter_son()
            dlg.reject()
        dlg.rejected.connect(on_reject)
        
        # Afficher et forcer au premier plan
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _notifier_systeme(self, titre, jour, heure):
        """Affiche une notification systeme via QSystemTrayIcon."""
        try:
            if not hasattr(self, "_tray_icon") or self._tray_icon is None:
                self._tray_icon = QSystemTrayIcon(self)
                icon_path = self.windowIcon() if not self.windowIcon().isNull() else QIcon()
                self._tray_icon.setIcon(icon_path)
                self._tray_icon.setVisible(True)
            msg = f"{titre}" + (f" à {heure}" if heure else f" le {jour}")
            self._tray_icon.showMessage(
                "🔔 Alarme Calendrier",
                msg,
                QSystemTrayIcon.Information,
                10000  # 10 secondes
            )
        except Exception:
            pass  # Silencieux si pas de system tray dispo

    def _jouer_son_test(self):
        """Joue le son d'alarme une fois (pour test bouton calendrier)."""
        try:
            from PyQt5.QtMultimedia import QSoundEffect
            from PyQt5.QtCore import QUrl
            from core.config import assurer_ressource
            son_path = assurer_ressource("alarm.wav")
            if son_path.exists():
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(son_path)))
                effect.setVolume(0.7)
                effect.play()
                if not hasattr(self, "_sons_actifs"):
                    self._sons_actifs = []
                self._sons_actifs.append(effect)
                QTimer.singleShot(5000, lambda: self._sons_actifs.remove(effect) if effect in self._sons_actifs else None)
            else:
                QApplication.beep()
        except Exception:
            QApplication.beep()

    # Alias pour compatibilite avec l'ancien code
    _jouer_son_alarme = _jouer_son_test

    def _synchroniser_badge(self):
        """Clic sur le badge : synchronisation manuelle immediate.

        Mode autonome : rien a synchroniser, on ouvre l'assistant
        multi-postes (ou on guide le gestionnaire) pour activer la
        connexion entre postes. Sinon on lance un pull structure/donnees/
        comptes puis la vide de la file en tache de fond.
        """
        from core import network
        if not network.sync_active():
            self._ouvrir_assistant_serveur()
            return
        from services.sync_service import synchroniser_maintenant

        self.lbl_api_status.setText("Synchro...")

        def _tirer():
            return synchroniser_maintenant()

        def _resultat(_res):
            self._refresh_api_status()

        run_async(_tirer, _resultat)

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

        Un clic sur le badge declenche une synchronisation immediate
        (ou ouvre l'assistant en mode autonome).
        """
        from core import network

        def _style(bg, fg):
            return (STYLE_BADGE_API
                    + f" background-color: {bg}; color: {fg};")

        self.lbl_api_status.setCursor(Qt.PointingHandCursor)

        if not network.sync_active():
            self.lbl_api_status.setText("Mode Autonome")
            self.lbl_api_status.setStyleSheet(
                _style(C_PRIMARY_LIGHT, C_PRIMARY_PRESSED))
            self.lbl_api_status.setToolTip(
                "Synchronisation entre postes desactivee. Clic : activer.")
            return

        if self._api_checking:
            return
        self._api_checking = True
        self.lbl_api_status.setText("Connexion...")
        self.lbl_api_status.setStyleSheet(
            _style(C_PRIMARY_LIGHT, C_PRIMARY_PRESSED))

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
                    _style(C_GREEN_BG, C_GREEN))
                self.lbl_api_status.setToolTip(
                    "Connecte au serveur de l'ecole. Clic : synchroniser.")
                motion.bounce_pulse(self.lbl_api_status, fois=2, duree=220)
            else:
                self.lbl_api_status.setText("Serveur Injoignable")
                self.lbl_api_status.setStyleSheet(_style(C_RED_BG, C_RED))
                self.lbl_api_status.setToolTip(
                    "Le logiciel ne rejoint pas le serveur de l'ecole.\n"
                    "Clic : reessayer.")

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
        # Fond Apple garanti : un widget dont le stylesheet est efface par
        # un builder (ou absent) devient transparent -> arriere-plan noir
        # visible a travers le contenu. On force la teinte BG sur la page
        # elle-meme (pas sur les enfants, qui gardent leurs propres styles).
        widget.setStyleSheet(
            f"QWidget#page_{page_name} {{ background-color: {C_BG}; }}")
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
        "lbl_section_outils": "Outils",
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
        "bloc_notes": "Notes personnelles",
        "calendrier": "Evenements et alarmes",
        "documents": "PDF generes, classement et export",
        "reseau": "Postes connectes et connexions",
        "rapports": "Exports PDF et syntheses",
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
