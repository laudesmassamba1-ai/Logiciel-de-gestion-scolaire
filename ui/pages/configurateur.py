"""Configurateur graphique de l'application — fenetre CACHEE (Ctrl+Shift+T).

Panel complet et « pousse » :
- COULEURS : 26 tokens du theme (apercu en direct a cote des reglages) ;
- TYPOGRAPHIE : polices corps/titres + tailles (titre de page, sous-titre,
  KPI, corps, legendes) ;
- BOUTONS & CHAMPS : rayons et paddings ;
- TABLEAUX : rayon, polices, paddings des cellules et de l'en-tete ;
- CARTES & FENETRES : rayon et padding des cartes ;
- SIDEBAR & KPI : largeur de la navigation, hauteur des cartes de chiffres ;
- PAGES : ordre, visibilite et ICONE (fa5s.*) de chaque entree de sidebar ;
- POSTE (LOCAL) : geometrie de la fenetre, etat maximise, page de demarrage —
  reglages propres a ce poste uniquement ;
- EXPORT / IMPORT : sauvegarde JSON, partage entre postes, copie dans le
  presse-papiers.

Un APERCU en direct (mini-ecran avec vrais widgets) est reconstruit a chaque
changement pour visualiser immediatement le resultat. Le theme est applique
au prochain demarrage (relu par resources.design_tokens et core.config).
"""

import json
import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from core.config import (
    APP_FONT_FAMILY, FONT_DISPLAY_FAMILY, C_CARD, C_BORDER, C_TEXT,
    C_TEXT_MUTED, C_TEXT_SECONDARY, C_GRAD_TOP, C_GRAD_BOTTOM, C_BG_SOFT,
    C_PRIMARY, C_PRIMARY_LIGHT, C_BORDER_STRONG, C_GRID, C_GREEN,
    C_FOCUS_RING, STYLE_BTN_PRIMARY, STYLE_HEADER_TITLE,
    T_TAILLE_TITRE_PAGE, T_TAILLE_SOUS_TITRE, T_RAYON_BTN,
    T_PAD_BTN_Y, T_PAD_BTN_X, T_RAYON_CHAMP, T_PAD_CHAMP_Y, T_PAD_CHAMP_X,
    T_RAYON_CARTE, T_PAD_CARTE, T_RAYON_TABLE, T_TABLE_FONT, T_TABLE_PAD_Y,
    T_TABLE_PAD_X, T_TABLE_HEADER_FONT, T_TABLE_HEADER_PAD_Y,
    T_TABLE_HEADER_PAD_X, T_KPI_HAUTEUR, T_SIDEBAR_LARGEUR,
)
from resources import design_tokens


_CHEMIN_THEME = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "theme_config.json",
)

_COULEURS_EDITABLES = [
    # --- Accent & degrade signature ---
    ("C_PRIMARY", "Accent principal (boutons, liens)", "Accent"),
    ("C_PRIMARY_HOVER", "Accent - survol", "Accent"),
    ("C_PRIMARY_PRESSED", "Accent - enfonce", "Accent"),
    ("C_PRIMARY_LIGHT", "Accent - fond selection", "Accent"),
    ("C_PRIMARY_BG", "Accent - fond pâle", "Accent"),
    ("C_PRIMARY_BORDER", "Accent - bordure", "Accent"),
    ("C_ACCENT_VIOLET", "Violet du degrade signature", "Accent"),
    ("C_GRAD_TOP", "Degrade signature - haut", "Accent"),
    ("C_GRAD_BOTTOM", "Degrade signature - bas", "Accent"),
    # --- Bleu & violet derives ---
    ("C_BLUE", "Bleu primaire", "Accent"),
    ("C_BLUE_HOVER", "Bleu - survol", "Accent"),
    ("C_BLUE_PRESSED", "Bleu - enfonce", "Accent"),
    ("C_BLUE_LIGHT", "Bleu - fond clair", "Accent"),
    ("C_BLUE_BORDER", "Bleu - bordure", "Accent"),
    ("C_VIOLET_HOVER", "Violet - survol", "Accent"),
    ("C_VIOLET_PRESSED", "Violet - enfonce", "Accent"),
    ("C_VIOLET_LIGHT", "Violet - fond clair", "Accent"),
    ("C_VIOLET_BORDER", "Violet - bordure", "Accent"),
    # --- Textes ---
    ("C_TEXT", "Texte principal", "Textes"),
    ("C_TEXT_SECONDARY", "Texte secondaire", "Textes"),
    ("C_TEXT_MUTED", "Texte mute (sous-titres)", "Textes"),
    ("C_TEXT_LIGHT", "Texte efface", "Textes"),
    ("C_EMPTY_STATE", "Etat vide (aucune donnee)", "Textes"),
    # --- Fonds, cartes, bordures ---
    ("C_BG", "Fond de page", "Fonds et cartes"),
    ("C_BG_SOFT", "Fond doux (en-tetes de table)", "Fonds et cartes"),
    ("C_BG_ALT", "Fond alterne (survol)", "Fonds et cartes"),
    ("C_CARD", "Carte / fond blanc", "Fonds et cartes"),
    ("C_BORDER", "Bordure hairline", "Fonds et cartes"),
    ("C_BORDER_STRONG", "Bordure forte", "Fonds et cartes"),
    ("C_CONTOUR", "Contour des sections (net)", "Fonds et cartes"),
    ("C_GRID", "Grille des tableaux", "Fonds et cartes"),
    ("C_FOCUS_RING", "Anneau de focus", "Fonds et cartes"),
    # --- Sidebar ---
    ("C_SIDEBAR_TEXT", "Sidebar - texte", "Sidebar"),
    ("C_SIDEBAR_MUTED", "Sidebar - texte muted", "Sidebar"),
    ("C_SIDEBAR_HOVER", "Sidebar - survol", "Sidebar"),
    ("C_SIDEBAR_ACTIVE", "Sidebar - fond actif", "Sidebar"),
    ("C_SIDEBAR_ACTIVE_TEXT", "Sidebar - texte actif", "Sidebar"),
    # --- Semantiques ---
    ("C_RED", "Danger / erreur", "Semantiques"),
    ("C_RED_HOVER", "Danger - survol", "Semantiques"),
    ("C_RED_PRESSED", "Danger - enfonce", "Semantiques"),
    ("C_RED_BG", "Danger - fond", "Semantiques"),
    ("C_RED_BORDER", "Danger - bordure", "Semantiques"),
    ("C_GREEN", "Succes / valide", "Semantiques"),
    ("C_GREEN_DARK", "Succes - fonce", "Semantiques"),
    ("C_GREEN_BG", "Succes - fond", "Semantiques"),
    ("C_GREEN_BORDER", "Succes - bordure", "Semantiques"),
    ("C_WARNING", "Avertissement", "Semantiques"),
    ("C_WARNING_HOVER", "Avertissement - survol", "Semantiques"),
    ("C_WARNING_PRESSED", "Avertissement - enfonce", "Semantiques"),
    ("C_WARNING_BG", "Avertissement - fond", "Semantiques"),
    ("C_WARNING_TEXT", "Avertissement - texte", "Semantiques"),
    ("C_INFO", "Info", "Semantiques"),
    ("C_INFO_BG", "Info - fond", "Semantiques"),
    ("C_INFO_BORDER", "Info - bordure", "Semantiques"),
    # --- Marque (or) ---
    ("C_GOLD", "Or (marque d'ecole)", "Marque"),
    ("C_GOLD_HOVER", "Or - survol", "Marque"),
    ("C_GOLD_PRESSED", "Or - enfonce", "Marque"),
    ("C_GOLD_LIGHT", "Or - fond clair", "Marque"),
    ("C_GOLD_BG", "Or - fond", "Marque"),
    ("C_GOLD_BORDER", "Or - bordure", "Marque"),
    ("C_GOLD_GRAD_TOP", "Or degrade - haut", "Marque"),
    ("C_GOLD_GRAD_BOTTOM", "Or degrade - bas", "Marque"),
]
_SECTIONS_COULEURS = ["Accent", "Textes", "Fonds et cartes", "Sidebar", "Semantiques", "Marque"]

# Composants cibles : chaque element de l'app peut avoir ses propres couleurs
# (liste eleves, emploi du temps, statuts financiers, graphiques). La cle de
# theme_config.json est "composants" -> {nom: {cle: hex}}.
_COMPOSANTS_EDITABLES = [
    ("eleves_table", "Liste des eleves",
     [("grille", "Grille du tableau"),
      ("fond_entete", "Fond de l'en-tete"),
      ("texte_entete", "Texte de l'en-tete"),
      ("fond_alternat", "Lignes alternees"),
      ("bordure", "Contour du tableau")]),
    ("planning", "Emploi du temps",
     [("grille", "Grille"),
      ("fond_entete", "Fond de l'en-tete"),
      ("texte_entete", "Texte de l'en-tete"),
      ("fond_cellule", "Fond des creneaux libres"),
      ("fond_occupe", "Fond des creneaux occupes"),
      ("texte_occupe", "Texte des creneaux occupes"),
      ("bordure", "Contour de la grille")]),
    ("statuts", "Statuts (paiements / presences)",
     [("paye", "Paiement paye"),
      ("du", "Paiement du"),
      ("retard", "Paiement en retard"),
      ("present", "Presence present"),
      ("absent", "Presence absent"),
      ("justifie", "Presence justifiee")]),
    ("statistiques", "Graphiques (barres, courbes...)",
     [("barres", "Barres"),
      ("courbe", "Courbes"),
      ("secteurs", "Secteurs (anneau)"),
      ("grille", "Grille de fond")]),
]

# Dims par section : (cle JSON, libelle, mini, maxi, valeur par defaut)
_DIMS_BOUTONS = [
    ("rayon_btn", "Rayon des boutons", 4, 24, T_RAYON_BTN),
    ("pad_btn_y", "Remplissage vertical", 2, 24, T_PAD_BTN_Y),
    ("pad_btn_x", "Remplissage horizontal", 6, 40, T_PAD_BTN_X),
]
_DIMS_CHAMPS = [
    ("rayon_champ", "Rayon des champs", 4, 24, T_RAYON_CHAMP),
    ("pad_champ_y", "Remplissage vertical", 2, 24, T_PAD_CHAMP_Y),
    ("pad_champ_x", "Remplissage horizontal", 6, 40, T_PAD_CHAMP_X),
]
_DIMS_TABLES = [
    ("rayon_table", "Rayon de la table", 4, 24, T_RAYON_TABLE),
    ("table_font", "Police des cellules", 11, 17, T_TABLE_FONT),
    ("table_pad_y", "Cellules - remplissage vertical", 2, 20, T_TABLE_PAD_Y),
    ("table_pad_x", "Cellules - remplissage horizontal", 4, 28, T_TABLE_PAD_X),
    ("table_header_font", "En-tete - police", 9, 15, T_TABLE_HEADER_FONT),
    ("table_header_pad_y", "En-tete - remplissage vertical", 4, 24, T_TABLE_HEADER_PAD_Y),
    ("table_header_pad_x", "En-tete - remplissage horizontal", 4, 28, T_TABLE_HEADER_PAD_X),
]
_DIMS_CARTES = [
    ("rayon_carte", "Rayon des cartes", 8, 28, T_RAYON_CARTE),
    ("pad_carte", "Remplissage interieur", 8, 32, T_PAD_CARTE),
]
_DIMS_SIDEBAR_KPI = [
    ("sidebar_largeur", "Largeur de la sidebar", 170, 320, T_SIDEBAR_LARGEUR),
    ("kpi_hauteur", "Hauteur des cartes KPI", 84, 160, T_KPI_HAUTEUR),
]
_DIMS_TYPO = [
    ("taille_titre_page", "Titre de page", 18, 40, T_TAILLE_TITRE_PAGE),
    ("taille_sous_titre", "Sous-titre de page", 11, 20, T_TAILLE_SOUS_TITRE),
    ("taille_corps", "Corps de texte", 11, 17, T_TABLE_FONT),
    ("taille_chiffres_kpi", "Grands chiffres (KPI)", 18, 44, design_tokens.FontSize.DISPLAY),
    ("taille_caption", "Legendes / notes", 9, 14, design_tokens.FontSize.CAPTION),
]


class ConfigurateurTheme(QDialog):
    """Fenetre cachee de configuration graphique complete (theme + poste)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration graphique")
        self.setMinimumSize(1180, 720)
        self.setModal(True)

        # Valeurs courantes de couleurs (theme en vigueur).
        from core import config as _cfg
        self._couleurs = {}
        for cle, _, _ in _COULEURS_EDITABLES:
            valeur = getattr(_cfg, cle, None) or _cfg.__dict__.get(cle)
            self._couleurs[cle] = valeur if isinstance(valeur, str) else "#FFFFFF"

        self._edits = {}
        self._swatches = {}
        self._comp_edits = {}     # composant -> cle -> QLineEdit
        self._comp_swatches = {}  # composant -> cle -> QPushButton
        self._spins = {}          # cle JSON -> QSpinBox
        self._combos = {}         # cle -> QComboBox
        self._checks = {}         # cle -> QCheckBox
        self._lst_pages = None
        self._icones = {}         # nom page -> icone fa5s courante
        self._defauts = {}        # nom page -> icone par defaut
        self._edit_icone = None
        self._apercu_conteneur = None
        self._apercu_body = None

        # Accroche live de l'apercu : un debounce limite les reconstructions
        # (cree AVANT l'UI : les premiers textChanged le declenchent).
        self._timer_apercu = QTimer(self)
        self._timer_apercu.setSingleShot(True)
        self._timer_apercu.setInterval(280)
        self._timer_apercu.timeout.connect(self._reconstruire_apercu)

        self._construire_ui()
        self._charger_valeurs()

    # ------------------------------------------------------------------
    # Construction generale
    # ------------------------------------------------------------------
    def _construire_ui(self):
        racine = QVBoxLayout(self)
        racine.setContentsMargins(20, 18, 20, 16)
        racine.setSpacing(12)

        titre = QLabel("Configuration graphique")
        titre.setStyleSheet(STYLE_HEADER_TITLE)
        sous_titre = QLabel(
            "Outil avance cache (Ctrl+Shift+T) : theme global et reglages "
            "locaux du poste. L'apercu a droite se met a jour en direct ; le "
            "theme est applique au prochain demarrage.")
        sous_titre.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        sous_titre.setWordWrap(True)
        racine.addWidget(titre)
        racine.addWidget(sous_titre)

        # Splitter : reglages a gauche, apercu en direct a droite.
        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(10)
        split.setChildrenCollapsible(False)

        onglets = QTabWidget()
        onglets.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {C_BORDER};"
            f" border-radius: 14px; background: {C_CARD}; }}"
            f"QTabBar::tab {{ background: transparent; padding: 9px 16px;"
            f" font-weight: 600; font-size: 13px; color: {C_TEXT_MUTED};"
            " border: none; border-bottom: 2px solid transparent; }"
            f"QTabBar::tab:selected {{ color: {C_TEXT};"
            f" border-bottom: 2px solid {C_PRIMARY}; }}"
            f"QTabBar::tab:hover {{ color: {C_TEXT}; }}"
        )
        onglets.addTab(self._onglet_couleurs(), "Couleurs")
        onglets.addTab(self._onglet_typo(), "Typographie")
        onglets.addTab(self._onglet_section(
            "Boutons & champs",
            [("Rayon et remplissage des boutons", _DIMS_BOUTONS),
             ("Rayon et remplissage des champs de saisie", _DIMS_CHAMPS)]),
            "Boutons & champs")
        onglets.addTab(self._onglet_section(
            "Tableaux",
            [("Mise en forme generale", _DIMS_TABLES)]),
            "Tableaux")
        onglets.addTab(self._onglet_section(
            "Cartes & fenetres",
            [("Cartes, fenetres, tableaux graphiques", _DIMS_CARTES)]),
            "Cartes & fenetres")
        onglets.addTab(self._onglet_section(
            "Sidebar & KPI",
            [("Navigation et cartes de chiffres", _DIMS_SIDEBAR_KPI)]),
            "Sidebar & KPI")
        onglets.addTab(self._onglet_composants(), "Composants")
        onglets.addTab(self._onglet_pages(), "Pages & icones")
        onglets.addTab(self._onglet_poste(), "Poste (local)")
        onglets.addTab(self._onglet_fichier(), "Export / Import")
        split.addWidget(onglets)

        apercu_panneau = self._construire_apercu_panneau()
        split.addWidget(apercu_panneau)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([780, 380])
        racine.addWidget(split, 1)

        # Pied : actions globales.
        pied = QHBoxLayout()
        pied.setSpacing(8)
        btn_defaut = QPushButton("Retablir le theme par defaut")
        btn_defaut.setStyleSheet(self._style_pied())
        btn_defaut.setCursor(Qt.PointingHandCursor)
        btn_defaut.clicked.connect(self._retablir_defaut)
        pied.addWidget(btn_defaut)
        pied.addStretch(1)
        btn_fermer = QPushButton("Fermer")
        btn_fermer.setStyleSheet(self._style_pied())
        btn_fermer.setCursor(Qt.PointingHandCursor)
        btn_fermer.clicked.connect(self.reject)
        btn_enregistrer = QPushButton("Enregistrer le theme")
        btn_enregistrer.setStyleSheet(STYLE_BTN_PRIMARY)
        btn_enregistrer.setCursor(Qt.PointingHandCursor)
        btn_enregistrer.clicked.connect(self._enregistrer)
        pied.addWidget(btn_fermer)
        pied.addWidget(btn_enregistrer)
        racine.addLayout(pied)

    @staticmethod
    def _style_pied():
        return (f"background: {C_BG_SOFT}; color: {C_TEXT};"
                f" border: 1px solid {C_BORDER}; border-radius: 12px;"
                " padding: 9px 16px; font-size: 13px;")

    # ------------------------------------------------------------------
    # Apercu en direct (panneau droit)
    # ------------------------------------------------------------------
    def _construire_apercu_panneau(self):
        panneau = QFrame()
        panneau.setStyleSheet(
            f"background: transparent; border: none;")
        lay = QVBoxLayout(panneau)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = QLabel("Apercu en direct")
        lbl.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-weight: 700; font-size: 12px;"
            " letter-spacing: 0.5px; text-transform: uppercase;")
        lay.addWidget(lbl)

        defile = QScrollArea()
        defile.setWidgetResizable(True)
        defile.setFrameShape(QFrame.NoFrame)
        conteneur = QWidget()
        conteneur.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #EAF2FF, stop:0.45 #F2EEFF, stop:1 #FBF4E6);"
            " border: none;")
        self._apercu_body = QVBoxLayout(conteneur)
        self._apercu_body.setContentsMargins(16, 16, 16, 16)
        self._apercu_body.setSpacing(10)
        self._apercu_conteneur = conteneur
        defile.setWidget(conteneur)
        lay.addWidget(defile, 1)
        return panneau

    def _valeur_couleur(self, cle):
        t = (self._edits[cle].text().strip() or "").upper()
        if len(t) == 7 and t.startswith("#"):
            try:
                int(t[1:], 16)
                return t
            except ValueError:
                pass
        return self._couleurs.get(cle) or "#FFFFFF"

    def _planifier_apercu(self, *_):
        if self._apercu_conteneur is not None:
            self._timer_apercu.start()

    def _reconstruire_apercu(self):
        if self._apercu_body is None:
            return
        # Vider le conteneur.
        while self._apercu_body.count():
            item = self._apercu_body.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        c = lambda cle: self._valeur_couleur(cle)
        pol_corps = self._combos["police_corps"].currentText().strip() or "Inter"
        pol_titres = self._combos["police_titres"].currentText().strip() or "Inter Display"

        def spinv(cle, defaut):
            s = self._spins.get(cle)
            return s.value() if s is not None else defaut

        # --- En-tete de page ---
        titre = QLabel("Eleves — apercu du theme")
        titre.setStyleSheet(
            f"font-family: '{pol_titres}', '{pol_corps}', 'Segoe UI', sans-serif;"
            f" font-size: {spinv('taille_titre_page', 26)}px; font-weight: 800;"
            f" letter-spacing: -0.4px; color: {c('C_TEXT')};"
            " background: transparent; border: none;")
        self._apercu_body.addWidget(titre)
        ss = QLabel("Apercu en direct : cartes, boutons, champs, tableaux")
        ss.setStyleSheet(
            f"font-size: {spinv('taille_sous_titre', 14)}px;"
            f" color: {c('C_TEXT_MUTED')};")
        self._apercu_body.addWidget(ss)

        # --- Boutons ---
        boutons = QHBoxLayout()
        boutons.setSpacing(8)
        r = spinv("rayon_btn", 12); py = spinv("pad_btn_y", 9); px = spinv("pad_btn_x", 18)
        b1 = QPushButton("Action principale")
        b1.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {c('C_GRAD_TOP')}, stop:1 {c('C_GRAD_BOTTOM')});"
            f" color: #FFFFFF; border: none; border-radius: {r}px;"
            f" padding: {py}px {px}px; font-weight: 600; font-size: 13px; }}")
        b2 = QPushButton("Secondaire")
        b2.setStyleSheet(
            f"QPushButton {{ background: #FFFFFF; color: {c('C_TEXT_SECONDARY')};"
            f" border: 1px solid {c('C_BORDER')}; border-radius: {r}px;"
            f" padding: {py}px {px}px; font-weight: 600; font-size: 13px; }}")
        b3 = QPushButton("Success")
        b3.setStyleSheet(
            f"QPushButton {{ background: {c('C_GREEN')}; color: #FFFFFF;"
            f" border: none; border-radius: {r}px; padding: {py}px {px}px;"
            " font-weight: 700; font-size: 13px; }}")
        boutons.addWidget(b1)
        boutons.addWidget(b2)
        boutons.addWidget(b3)
        boutons.addStretch(1)
        self._apercu_body.addLayout(boutons)

        # --- Champs ---
        rch = spinv("rayon_champ", 12); cy = spinv("pad_champ_y", 7); cx = spinv("pad_champ_x", 13)
        qss_champ = (
            f"QLineEdit {{ border: 1px solid {c('C_BORDER_STRONG')};"
            f" border-radius: {rch}px; min-height: 24px;"
            f" padding: {cy}px {cx}px; background-color: #FFFFFF;"
            f" color: {c('C_TEXT')}; font-size: {spinv('taille_corps', 13)}px; }}"
            f"QLineEdit:focus {{ border: 2px solid {c('C_FOCUS_RING')}; }}")
        saisie = QLineEdit()
        saisie.setPlaceholderText("Rechercher un eleve...")
        saisie.setStyleSheet(qss_champ)
        self._apercu_body.addWidget(saisie)

        # --- Carte STYLE_CARD ---
        carte = QFrame()
        carte.setStyleSheet(
            f"QFrame {{ background: {c('C_CARD')}; border: 1px solid {c('C_BORDER')};"
            f" border-radius: {spinv('rayon_carte', 16)}px;"
            f" padding: {spinv('pad_carte', 16)}px; }}")
        carte_lay = QVBoxLayout(carte)
        carte_lay.setContentsMargins(14, 12, 14, 12)
        lbl_carte = QLabel("Carte d'information")
        lbl_carte.setStyleSheet(
            f"color: {c('C_TEXT')}; font-weight: 700; font-size: 14px;"
            " background: transparent;")
        lbl_carte2 = QLabel("Contenu de la carte : le rayon et le remplissage "
                            "suivent vos reglages.")
        lbl_carte2.setWordWrap(True)
        lbl_carte2.setStyleSheet(f"color: {c('C_TEXT_MUTED')}; font-size: 12px;")
        carte_lay.addWidget(lbl_carte)
        carte_lay.addWidget(lbl_carte2)
        self._apercu_body.addWidget(carte)

        # --- KPI reel ---
        try:
            from ui.widgets.kpi_card import KPICard
            kpi = KPICard("Effectifs", "1 248", couleur=c("C_PRIMARY"))
            kpi.setFixedHeight(spinv("kpi_hauteur", 112))
            kpi._valeur.setStyleSheet(
                f"font-family: '{pol_titres}', '{pol_corps}', 'Segoe UI', sans-serif;"
                f" font-size: {spinv('taille_chiffres_kpi', 26)}px;"
                f" font-weight: 800; letter-spacing: -0.5px; color: {c('C_PRIMARY')};"
                " border: none; background: transparent;")
            kpi._label.setStyleSheet(
                f"color: {c('C_TEXT_MUTED')}; font-size: 10px; font-weight: 700;"
                " text-transform: uppercase; letter-spacing: 1.2px;"
                " border: none; background: transparent;")
            self._apercu_body.addWidget(kpi)
        except Exception:
            pass

        # --- Tableau ---
        th = spinv("table_header_font", 11); th_y = spinv("table_header_pad_y", 11)
        th_x = spinv("table_header_pad_x", 12)
        tf = spinv("table_font", 13); t_y = spinv("table_pad_y", 9); t_x = spinv("table_pad_x", 12)
        qss_table = (
            f"QTableWidget {{ background: {c('C_CARD')};"
            f" alternate-background-color: {c('C_BG_SOFT')};"
            f" border: 1px solid {c('C_BORDER')};"
            f" border-radius: {spinv('rayon_table', 14)}px;"
            f" gridline-color: {c('C_GRID')}; font-size: {tf}px; }}"
            f"QHeaderView::section {{ background: {c('C_BG_SOFT')};"
            f" color: {c('C_TEXT_SECONDARY')}; font-weight: 700;"
            f" font-size: {th}px; letter-spacing: 0.6px;"
            " text-transform: uppercase; border: none;"
            f" border-bottom: 2px solid {c('C_BORDER_STRONG')};"
            f" padding: {th_y}px {th_x}px; }}"
            f"QTableWidget::item {{ padding: {t_y}px {t_x}px;"
            f" border-bottom: 1px solid {c('C_GRID')}; }}")
        table = QTableWidget(3, 3)
        table.setHorizontalHeaderLabels(["Nom", "Classe", "Statut"])
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, (nom, cls, statut) in enumerate([
                ("KONE Ibrahim", "6eme A", "Paye"),
                ("MBEMBA Lea", "6eme A", "Du"),
                ("NGOMA Ariel", "5eme B", "Paye")]):
            table.setItem(i, 0, QTableWidgetItem(nom))
            table.setItem(i, 1, QTableWidgetItem(cls))
            table.setItem(i, 2, QTableWidgetItem(statut))
        table.setStyleSheet(qss_table)
        table.setFixedHeight(190)
        self._apercu_body.addWidget(table)

        self._apercu_body.addStretch(1)

    # ------------------------------------------------------------------
    # Onglet Composants (elements cibles : eleves, planning, statuts...)
    # ------------------------------------------------------------------
    def _onglet_composants(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(8)

        intro = QLabel(
            "Réglages ciblés par élément de l'application : la liste des "
            "eleves, l'emploi du temps, les statuts des paiements/presences "
            "et les graphiques ont leurs propres couleurs, independantes du "
            "theme global. Appliques au prochain demarrage.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        lay.addWidget(intro)

        defile = QScrollArea()
        defile.setWidgetResizable(True)
        defile.setFrameShape(QFrame.NoFrame)
        conteneur = QWidget()
        int_lay = QVBoxLayout(conteneur)
        int_lay.setContentsMargins(4, 4, 12, 4)
        int_lay.setSpacing(6)

        from core.config import lire_composant
        for nom, titre, cles in _COMPOSANTS_EDITABLES:
            int_lay.addWidget(self._cadre_section(titre))
            courant = lire_composant(nom)
            self._comp_edits.setdefault(nom, {})
            self._comp_swatches.setdefault(nom, {})
            for cle, libelle in cles:
                ligne = QWidget()
                l_l = QHBoxLayout(ligne)
                l_l.setContentsMargins(0, 0, 0, 0)
                l_l.setSpacing(10)

                swatch = QPushButton()
                swatch.setFixedSize(26, 26)
                swatch.setCursor(Qt.PointingHandCursor)
                swatch.setToolTip("Choisir une couleur...")
                swatch.clicked.connect(
                    lambda _, c=nom, k=cle: self._choisir_couleur_comp(c, k))
                self._comp_swatches[nom][cle] = swatch

                edit = QLineEdit()
                edit.setFixedWidth(96)
                edit.setMaxLength(7)
                edit.setText(str(courant.get(cle, "#FFFFFF")).upper())
                edit.setStyleSheet(
                    f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER};"
                    f" border-radius: 8px; padding: 5px 8px; font-size: 12px;"
                    f" color: {C_TEXT};")
                edit.textChanged.connect(
                    lambda _, c=nom: self._rafraichir_swatch_comp(c))
                edit.textChanged.connect(self._planifier_apercu)
                self._comp_edits[nom][cle] = edit

                lbl = QLabel(libelle)
                lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")

                l_l.addWidget(swatch)
                l_l.addWidget(edit)
                l_l.addWidget(lbl, 1)
                int_lay.addWidget(ligne)
                swatch.setStyleSheet(
                    f"background: {edit.text().strip()};"
                    f" border: 1px solid {C_BORDER}; border-radius: 7px;")
        int_lay.addStretch(1)
        defile.setWidget(conteneur)
        lay.addWidget(defile, 1)
        return page

    def _choisir_couleur_comp(self, nom, cle):
        edit = self._comp_edits[nom][cle]
        actuel = QColor(edit.text().strip() or "#FFFFFF")
        choisi = QColorDialog.getColor(actuel, self, f"Couleur : {nom}.{cle}")
        if choisi.isValid():
            edit.setText(choisi.name().upper())

    def _rafraichir_swatch_comp(self, nom):
        for cle, edit in self._comp_edits.get(nom, {}).items():
            hexa = edit.text().strip()
            couleur = QColor(hexa) if QColor(hexa).isValid() else QColor("#FFFFFF")
            self._comp_swatches[nom][cle].setStyleSheet(
                f"background: {couleur.name()}; border: 1px solid {C_BORDER};"
                " border-radius: 7px;")

    # ------------------------------------------------------------------
    # Onglet Couleurs
    # ------------------------------------------------------------------
    def _onglet_couleurs(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(8)

        defile = QScrollArea()
        defile.setWidgetResizable(True)
        defile.setFrameShape(QFrame.NoFrame)
        conteneur = QWidget()
        int_lay = QVBoxLayout(conteneur)
        int_lay.setContentsMargins(4, 4, 12, 4)
        int_lay.setSpacing(6)

        for section in _SECTIONS_COULEURS:
            int_lay.addWidget(self._cadre_section(section))
            for cle, libelle, sec in _COULEURS_EDITABLES:
                if sec != section:
                    continue
                int_lay.addWidget(self._ligne_couleur(cle, libelle))
        int_lay.addStretch(1)
        defile.setWidget(conteneur)
        lay.addWidget(defile, 1)
        return page

    def _ligne_couleur(self, cle, libelle):
        ligne = QWidget()
        lay = QHBoxLayout(ligne)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        swatch = QPushButton()
        swatch.setFixedSize(26, 26)
        swatch.setCursor(Qt.PointingHandCursor)
        swatch.setToolTip("Choisir une couleur...")
        swatch.clicked.connect(lambda: self._choisir_couleur(cle))
        self._swatches[cle] = swatch

        edit = QLineEdit()
        edit.setFixedWidth(96)
        edit.setMaxLength(7)
        edit.setStyleSheet(
            f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER};"
            f" border-radius: 8px; padding: 5px 8px; font-size: 12px; color: {C_TEXT};")
        edit.textChanged.connect(self._rafraichir_swatch)
        edit.textChanged.connect(self._planifier_apercu)
        self._edits[cle] = edit

        lbl = QLabel(libelle)
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")

        lay.addWidget(swatch)
        lay.addWidget(edit)
        lay.addWidget(lbl, 1)
        return ligne

    def _choisir_couleur(self, cle):
        actuel = QColor(self._edits[cle].text().strip() or "#FFFFFF")
        choisi = QColorDialog.getColor(actuel, self, f"Couleur : {cle}")
        if choisi.isValid():
            self._edits[cle].setText(choisi.name().upper())

    def _rafraichir_swatch(self, texte, cle=None):
        for cle in self._edits:
            hexa = self._edits[cle].text().strip()
            couleur = QColor(hexa) if QColor(hexa).isValid() else QColor("#FFFFFF")
            self._swatches[cle].setStyleSheet(
                f"background: {couleur.name()}; border: 1px solid {C_BORDER};"
                " border-radius: 7px;")

    @staticmethod
    def _hex_valide(texte):
        t = (texte or "").strip().upper()
        if len(t) == 7 and t.startswith("#"):
            try:
                int(t[1:], 16)
                return t
            except ValueError:
                return ""
        return ""

    # ------------------------------------------------------------------
    # Onglet Typographie
    # ------------------------------------------------------------------
    def _onglet_typo(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(12)
        familles = sorted(set(QFontDatabase().families()))

        self._combos["police_corps"] = self._ligne_combo(
            "Police du corps de texte", familles, APP_FONT_FAMILY, lay)
        self._combos["police_titres"] = self._ligne_combo(
            "Police des titres et grands chiffres", familles,
            FONT_DISPLAY_FAMILY, lay)

        lay.addWidget(self._cadre_section("Tailles (px)"))
        for cle, libelle, mini, maxi, defaut in _DIMS_TYPO:
            self._ligne_spin(cle, libelle, mini, maxi, lay, defaut=defaut)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Onglet generique « section de dimensions »
    # ------------------------------------------------------------------
    def _onglet_section(self, titre_section, groupes):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(12)
        for libelle_groupe, dims in groupes:
            lay.addWidget(self._cadre_section(libelle_groupe))
            for cle, libelle, mini, maxi, defaut in dims:
                self._ligne_spin(cle, libelle, mini, maxi, lay, defaut=defaut)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Onglet Pages & icones
    # ------------------------------------------------------------------
    def _onglet_pages(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(10)

        intro = QLabel(
            "Ordre de la sidebar : cochez pour afficher, decochez pour "
            "masquer, fleches pour reordonner. L'icone (Font Awesome 5, "
            "format fa5s.nom) remplace celle par defaut en cas de nom valide.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        lay.addWidget(intro)

        self._lst_pages = QListWidget()
        self._lst_pages.setStyleSheet(
            f"QListWidget {{ background: {C_CARD}; border: 1px solid {C_BORDER};"
            f" border-radius: 12px; font-size: 13px; color: {C_TEXT}; }}"
            f"QListWidget::item {{ padding: 7px 10px;"
            f" border-bottom: 1px solid {C_BG_SOFT}; }}"
            f"QListWidget::item:selected {{ background: {C_PRIMARY_LIGHT};"
            f" color: {C_TEXT}; }}")
        self._lst_pages.itemChanged.connect(self._planifier_apercu)

        from ui.main_view import NAV_PAGES, PAGE_TITRES
        self._ordre_defaut = list(NAV_PAGES.values())
        self._titres = PAGE_TITRES

        boutons_ord = QVBoxLayout()
        boutons_ord.setSpacing(8)
        btn_mont = QPushButton("\u25B2 Monter")
        btn_desc = QPushButton("\u25BC Descendre")
        btn_defaut = QPushButton("Ordre par defaut")
        for b in (btn_mont, btn_desc, btn_defaut):
            b.setStyleSheet(self._style_pied())
            b.setCursor(Qt.PointingHandCursor)
        btn_mont.clicked.connect(lambda: self._deplacer(-1))
        btn_desc.clicked.connect(lambda: self._deplacer(1))
        btn_defaut.clicked.connect(self._ordre_par_defaut)
        boutons_ord.addWidget(btn_mont)
        boutons_ord.addWidget(btn_desc)
        boutons_ord.addWidget(btn_defaut)
        boutons_ord.addStretch(1)

        corps = QHBoxLayout()
        corps.setSpacing(12)
        corps.addWidget(self._lst_pages, 1)
        corps.addLayout(boutons_ord)
        lay.addLayout(corps, 1)

        # Edition de l'icone de la page selectionnee (FA5).
        ligne_icone = QWidget()
        lay_i = QHBoxLayout(ligne_icone)
        lay_i.setContentsMargins(0, 0, 0, 0)
        lay_i.setSpacing(10)
        lbl_i = QLabel("Icône de la page selectionnee")
        lbl_i.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        self._edit_icone = QLineEdit()
        self._edit_icone.setPlaceholderText("fa5s.nom_de_l_icone  (ex : fa5s.chart-line)")
        self._edit_icone.setMinimumWidth(320)
        self._edit_icone.setStyleSheet(
            f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px; padding: 7px 13px; font-size: 13px;"
            f" color: {C_TEXT};")
        self._edit_icone.textEdited.connect(self._maj_icone_page)
        lay_i.addWidget(lbl_i, 1)
        lay_i.addWidget(self._edit_icone)
        lay.addWidget(ligne_icone)
        self._lst_pages.currentRowChanged.connect(self._maj_champ_icone)

        expl = QLabel(
            "Icônes Font Awesome 5 : format « fa5s.nom » (exemples : "
            "fa5s.user-graduate, fa5s.money-bill-alt, fa5s.chart-line, "
            "fa5s.book-open, fa5s.cog, fa5s.folder-open). Un nom invalide "
            "laisse l'icone par defaut.")
        expl.setWordWrap(True)
        expl.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        lay.addWidget(expl)
        return page

    def _maj_champ_icone(self, row):
        if row is None or row < 0:
            return
        item = self._lst_pages.item(row)
        if item is None:
            return
        nom = item.data(Qt.UserRole)
        self._edit_icone.setText(self._icones.get(nom, ""))

    def _maj_icone_page(self, texte):
        row = self._lst_pages.currentRow()
        if row < 0:
            return
        item = self._lst_pages.item(row)
        if item is None:
            return
        nom = item.data(Qt.UserRole)
        icone = (texte or "").strip()
        self._icones[nom] = icone
        libelle = self._titres.get(nom, nom)
        if icone and icone != self._defauts.get(nom, ""):
            item.setText(f"{libelle}   [{icone}]")
        else:
            item.setText(libelle)
        self._planifier_apercu()

    def _deplacer(self, sens):
        ligne = self._lst_pages.currentRow()
        if ligne < 0:
            return
        cible = ligne + sens
        if cible < 0 or cible >= self._lst_pages.count():
            return
        item = self._lst_pages.takeItem(ligne)
        self._lst_pages.insertItem(cible, item)
        self._lst_pages.setCurrentRow(cible)
        self._planifier_apercu()

    def _ordre_par_defaut(self):
        noms = list(self._ordre_defaut)
        etats = {self._lst_pages.item(i).data(Qt.UserRole):
                 self._lst_pages.item(i).checkState()
                 for i in range(self._lst_pages.count())}
        self._lst_pages.clear()
        for nom in noms:
            item = QListWidgetItem(self._titres.get(nom, nom))
            item.setData(Qt.UserRole, nom)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(etats.get(nom, Qt.Checked))
            icone = (self._icones.get(nom) or "").strip()
            if icone and icone != self._defauts.get(nom, ""):
                item.setText(f"{self._titres.get(nom, nom)}   [{icone}]")
            self._lst_pages.addItem(item)
        self._planifier_apercu()

    # ------------------------------------------------------------------
    # Onglet Poste (LOCAL)
    # ------------------------------------------------------------------
    def _onglet_poste(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(12)

        intro = QLabel(
            "Reglages LOCAUX : propres a ce poste uniquement (non exportes "
            "avec le theme partage). Appliques au demarrage de l'application.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        lay.addWidget(intro)

        lay.addWidget(self._cadre_section("Fenetre principale"))
        self._ligne_spin("largeur_fenetre", "Largeur de la fenetre", 900, 2600, lay,
                         defaut=1280, suffixe=" px")
        self._ligne_spin("hauteur_fenetre", "Hauteur de la fenetre", 600, 1600, lay,
                         defaut=800, suffixe=" px")

        ligne = QWidget()
        lay_l = QHBoxLayout(ligne)
        lay_l.setContentsMargins(0, 0, 0, 0)
        lay_l.setSpacing(10)
        lbl = QLabel("Demarrer en plein ecran")
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        chk = QCheckBox()
        chk.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; }")
        chk.setChecked(True)
        chk.stateChanged.connect(self._planifier_apercu)
        lay_l.addWidget(lbl, 1)
        lay_l.addWidget(chk)
        lay.addWidget(ligne)
        self._checks["maximise"] = chk

        # Page de demarrage
        from ui.main_view import PAGE_TITRES
        demarrage = QWidget()
        lay_d = QHBoxLayout(demarrage)
        lay_d.setContentsMargins(0, 0, 0, 0)
        lay_d.setSpacing(10)
        lbl_d = QLabel("Page ouverte au demarrage")
        lbl_d.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        combo_d = QComboBox()
        combo_d.setEditable(False)
        combo_d.addItems(list(PAGE_TITRES.values()))
        combo_d.setStyleSheet(self._qss_combo())
        combo_d.currentIndexChanged.connect(self._planifier_apercu)
        lay_d.addWidget(lbl_d, 1)
        lay_d.addWidget(combo_d)
        lay.addWidget(demarrage)
        self._combos["page_demarrage"] = combo_d

        lay.addWidget(self._cadre_section("Memo"))
        note = QLabel(
            "Couleurs, typographie, dimensions, pages et icones = theme "
            "GLOBAL (partage entre postes via Export/Import).\n"
            "Taille de fenetre, plein ecran et page de demarrage = LOCAL "
            "a ce poste (sauvegardes dans le meme fichier, ignores ailleurs).")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        lay.addWidget(note)
        lay.addStretch(1)
        return page

    def _qss_combo(self):
        return (f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER};"
                " border-radius: 10px; padding: 6px 10px; font-size: 13px;"
                f" color: {C_TEXT}; min-height: 22px;")

    # ------------------------------------------------------------------
    # Onglet Export / Import
    # ------------------------------------------------------------------
    def _onglet_fichier(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(12)

        expl = QLabel("Le theme est enregistre dans le fichier :")
        expl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        chemin = QLabel(_CHEMIN_THEME)
        chemin.setStyleSheet(
            f"background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            " padding: 10px 14px; font-size: 12px;")
        chemin.setWordWrap(True)
        lay.addWidget(expl)
        lay.addWidget(chemin)

        txt = QLabel(
            "Exporter : sauvegarde le theme actuel dans un fichier JSON a "
            "partager entre postes (coller le fichier sur un autre poste puis "
            "« Importer un theme »).\n\n"
            "Copier : place le JSON dans le presse-papiers, a coller tel quel "
            "(email, tchat) ailleurs.\n\n"
            "Importer : charge un theme JSON precedent et remplit la fenetre "
            "avec (pensez ensuite a « Enregistrer le theme »).")
        txt.setWordWrap(True)
        txt.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        lay.addWidget(txt)

        boutons = QHBoxLayout()
        boutons.setSpacing(10)
        btn_copier = QPushButton("Copier le JSON")
        btn_exp = QPushButton("Exporter le theme...")
        btn_imp = QPushButton("Importer un theme...")
        for b in (btn_copier, btn_exp, btn_imp):
            b.setStyleSheet(self._style_pied())
            b.setCursor(Qt.PointingHandCursor)
        btn_copier.clicked.connect(self._copier_json)
        btn_exp.clicked.connect(self._exporter)
        btn_imp.clicked.connect(self._importer)
        boutons.addWidget(btn_copier)
        boutons.addWidget(btn_exp)
        boutons.addWidget(btn_imp)
        boutons.addStretch(1)
        lay.addLayout(boutons)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Widgets de ligne generiques
    # ------------------------------------------------------------------
    def _cadre_section(self, titre_section):
        lbl = QLabel(titre_section)
        lbl.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-weight: 700; font-size: 12px;"
            " letter-spacing: 0.5px; text-transform: uppercase; padding: 2px 0;")
        cadre = QFrame()
        cadre.setFixedHeight(1)
        cadre.setStyleSheet(f"background: {C_BORDER}; border: none;")
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 6, 0, 4)
        lay.setSpacing(6)
        lay.addWidget(lbl)
        lay.addWidget(cadre)
        conteneur = QWidget()
        conteneur.setLayout(lay)
        return conteneur

    def _ligne_combo(self, libelle, valeurs, actuel, lay_parent):
        ligne = QWidget()
        lay = QHBoxLayout(ligne)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lbl = QLabel(libelle)
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(valeurs)
        combo.setCurrentText(actuel or "")
        combo.setStyleSheet(self._qss_combo())
        combo.currentIndexChanged.connect(self._planifier_apercu)
        combo.lineEdit().textEdited.connect(self._planifier_apercu)
        combo.setMinimumWidth(240)
        lay.addWidget(lbl, 1)
        lay.addWidget(combo, 1)
        lay_parent.addWidget(ligne)
        return combo

    def _ligne_spin(self, cle, libelle, mini, maxi, lay_parent, defaut=0,
                    suffixe=" px"):
        ligne = QWidget()
        lay = QHBoxLayout(ligne)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lbl = QLabel(libelle)
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        spin = QSpinBox()
        spin.setRange(mini, maxi)
        spin.setValue(int(defaut))
        spin.setSuffix(suffixe)
        spin.setStyleSheet(self._qss_combo())
        spin.valueChanged.connect(self._planifier_apercu)
        spin.setMinimumWidth(130)
        lay.addWidget(lbl, 1)
        lay.addWidget(spin)
        lay_parent.addWidget(ligne)
        self._spins[cle] = spin
        return spin

    # ------------------------------------------------------------------
    # Chargement / collecte / enregistrement
    # ------------------------------------------------------------------
    def _charger_valeurs(self):
        # Couleurs
        for cle, _, _ in _COULEURS_EDITABLES:
            self._edits[cle].setText((self._couleurs.get(cle) or "#FFFFFF").upper())
        self._rafraichir_swatch(None)

        # Pages : ordre applique par le theme en vigueur, sinon defaut.
        from ui.main_view import NAV_PAGES, ICONES_DEFAUTS
        theme_actuel = getattr(design_tokens, "THEME_BRUT", {}) or {}
        masquees = set((theme_actuel.get("pages") or {}).get("masquees") or [])
        icones_theme = (theme_actuel.get("icones") or {})
        self._defauts = {NAV_PAGES[b]: ic for b, ic in ICONES_DEFAUTS.items()
                         if b in NAV_PAGES}
        for nom in self._ordre_defaut:
            icone = icones_theme.get(nom) or self._defauts.get(nom, "")
            self._icones[nom] = icone
            item = QListWidgetItem(self._titres.get(nom, nom))
            item.setData(Qt.UserRole, nom)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if nom in masquees else Qt.Checked)
            if icone and icone != self._defauts.get(nom, ""):
                item.setText(f"{self._titres.get(nom, nom)}   [{icone}]")
            self._lst_pages.addItem(item)
        self._lst_pages.setCurrentRow(0)

        # Poste (local)
        local_cfg = (theme_actuel.get("local") or {})
        try:
            lw = int(local_cfg.get("largeur_fenetre") or 0)
        except (TypeError, ValueError):
            lw = 0
        try:
            lh = int(local_cfg.get("hauteur_fenetre") or 0)
        except (TypeError, ValueError):
            lh = 0
        if lw >= 900:
            self._spins["largeur_fenetre"].setValue(lw)
        if lh >= 600:
            self._spins["hauteur_fenetre"].setValue(lh)
        self._checks["maximise"].setChecked(bool(local_cfg.get("maximise", True)))
        demarrage = local_cfg.get("page_demarrage") or "dashboard"
        titre_demarrage = self._titres.get(demarrage, self._titres["dashboard"])
        idx = self._combos["page_demarrage"].findText(titre_demarrage)
        if idx >= 0:
            self._combos["page_demarrage"].setCurrentIndex(idx)

        # Composants : valeurs du theme en vigueur (sinon defauts du module).
        composants_theme = (theme_actuel.get("composants") or {})
        for nom, _, cles in _COMPOSANTS_EDITABLES:
            courant = composants_theme.get(nom) or {}
            for cle, _ in cles:
                edit = self._comp_edits.get(nom, {}).get(cle)
                if edit is None:
                    continue
                val = courant.get(cle) or "#FFFFFF"
                edit.setText(str(val).upper())
                self._rafraichir_swatch_comp(nom)

    def _recueillir(self):
        couleurs = {}
        for cle, _, _ in _COULEURS_EDITABLES:
            t = self._hex_valide(self._edits[cle].text())
            couleurs[cle] = t or self._couleurs[cle]

        typo = {
            "police_corps": self._combos["police_corps"].currentText().strip(),
            "police_titres": self._combos["police_titres"].currentText().strip(),
        }

        dimensions = {}
        for cle, spin in self._spins.items():
            if cle in ("largeur_fenetre", "hauteur_fenetre"):
                continue  # c'est du LOCAL (section "local"), pas une dimension
            dimensions[cle] = spin.value()

        pages = {"ordre": [], "masquees": []}
        icones = {}
        for i in range(self._lst_pages.count()):
            item = self._lst_pages.item(i)
            nom = item.data(Qt.UserRole)
            pages["ordre"].append(nom)
            if item.checkState() != Qt.Checked:
                pages["masquees"].append(nom)
            icone = (self._icones.get(nom) or "").strip()
            if icone and icone != self._defauts.get(nom, ""):
                icones[nom] = icone

        local = {
            "largeur_fenetre": self._spins["largeur_fenetre"].value(),
            "hauteur_fenetre": self._spins["hauteur_fenetre"].value(),
            "maximise": self._checks["maximise"].isChecked(),
            "page_demarrage": self._page_par_titre(
                self._combos["page_demarrage"].currentText()),
        }

        composants = {}
        for nom, _, cles in _COMPOSANTS_EDITABLES:
            composants[nom] = {}
            for cle, _ in cles:
                edit = self._comp_edits.get(nom, {}).get(cle)
                if edit is None:
                    continue
                t = self._hex_valide(edit.text())
                composants[nom][cle] = t or "#FFFFFF"

        return {"couleurs": couleurs, "typo": typo, "dimensions": dimensions,
                "pages": pages, "icones": icones, "local": local,
                "composants": composants}

    def _page_par_titre(self, titre):
        for nom, t in self._titres.items():
            if t == titre:
                return nom
        return "dashboard"

    def _ecrire(self, donnees):
        dossier = os.path.dirname(_CHEMIN_THEME)
        if dossier and not os.path.isdir(dossier):
            os.makedirs(dossier, exist_ok=True)
        with open(_CHEMIN_THEME, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)

    def _enregistrer(self):
        donnees = self._recueillir()
        try:
            self._ecrire(donnees)
        except OSError as exc:
            QMessageBox.critical(self, "Erreur",
                                 f"Impossible d'ecrire le theme :\n{exc}")
            return
        reponse = QMessageBox.question(
            self, "Theme enregistre",
            "Theme enregistre dans data/theme_config.json.\n\n"
            "Il sera applique au prochain demarrage de l'application.\n"
            "Voulez-vous redemarrer maintenant ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reponse == QMessageBox.Yes:
            self._redemarrer()

    def _retablir_defaut(self):
        reponse = QMessageBox.question(
            self, "Retablir le theme par defaut",
            "Retablir le theme Liquid Glass d'origine ?\n\n"
            "Le fichier data/theme_config.json sera supprime et l'appli "
            "reviendra a ses valeurs par defaut.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reponse != QMessageBox.Yes:
            return
        try:
            if os.path.exists(_CHEMIN_THEME):
                os.remove(_CHEMIN_THEME)
        except OSError as exc:
            QMessageBox.critical(self, "Erreur",
                                 f"Suppression impossible :\n{exc}")
            return
        reponse = QMessageBox.question(
            self, "Theme retabli",
            "Le theme par defaut sera applique au prochain demarrage.\n"
            "Voulez-vous redemarrer maintenant ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reponse == QMessageBox.Yes:
            self._redemarrer()

    def _copier_json(self):
        donnees = self._recueillir()
        QApplication.clipboard().setText(
            json.dumps(donnees, ensure_ascii=False, indent=2))
        QMessageBox.information(
            self, "JSON copie",
            "Le theme (JSON) est dans le presse-papiers.\nCollez-le ailleurs "
            "ou sur un autre poste pour le partager.")

    def _exporter(self):
        donnees = self._recueillir()
        cible, _ = QFileDialog.getSaveFileName(
            self, "Exporter le theme", "theme_config.json",
            "Theme JSON (*.json)")
        if not cible:
            return
        try:
            with open(cible, "w", encoding="utf-8") as f:
                json.dump(donnees, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Theme exporte",
                                    f"Theme exporte vers :\n{cible}")
        except OSError as exc:
            QMessageBox.critical(self, "Erreur", f"Export impossible :\n{exc}")

    def _importer(self):
        source, _ = QFileDialog.getOpenFileName(
            self, "Importer un theme", "", "Theme JSON (*.json)")
        if not source:
            return
        try:
            with open(source, "r", encoding="utf-8") as f:
                donnees = json.load(f)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Erreur",
                                 f"Fichier illisible ou invalide :\n{exc}")
            return
        if not isinstance(donnees, dict) or "couleurs" not in donnees:
            QMessageBox.critical(self, "Erreur",
                                 "Ce fichier n'est pas un theme valide.")
            return
        couleurs = donnees.get("couleurs") or {}
        for cle, _, _ in _COULEURS_EDITABLES:
            if cle in couleurs:
                self._edits[cle].setText(str(couleurs[cle]).upper())
        self._combos["police_corps"].setCurrentText(
            str((donnees.get("typo") or {}).get("police_corps") or ""))
        self._combos["police_titres"].setCurrentText(
            str((donnees.get("typo") or {}).get("police_titres") or ""))
        dims = donnees.get("dimensions") or {}
        for cle, spin in self._spins.items():
            if cle in dims:
                try:
                    spin.setValue(int(dims[cle]))
                except (TypeError, ValueError):
                    pass
        local = donnees.get("local") or {}
        try:
            lw = int(local.get("largeur_fenetre") or 0)
            lh = int(local.get("hauteur_fenetre") or 0)
            if lw >= 900:
                self._spins["largeur_fenetre"].setValue(lw)
            if lh >= 600:
                self._spins["hauteur_fenetre"].setValue(lh)
        except (TypeError, ValueError):
            pass
        self._checks["maximise"].setChecked(bool(local.get("maximise", True)))
        composants_imp = donnees.get("composants") or {}
        for nom, _, cles in _COMPOSANTS_EDITABLES:
            courant = composants_imp.get(nom) or {}
            for cle, _ in cles:
                edit = self._comp_edits.get(nom, {}).get(cle)
                if edit is None or cle not in courant:
                    continue
                edit.setText(str(courant[cle]).upper())
            self._rafraichir_swatch_comp(nom)
        QMessageBox.information(
            self, "Theme importe",
            "Theme charge dans cette fenetre.\nCliquez sur "
            "« Enregistrer le theme » pour l'appliquer.")

    def _redemarrer(self):
        import subprocess
        script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "scripts", "lancer_synchronise.sh")
        if os.path.exists(script):
            try:
                subprocess.Popen(
                    ["bash", script],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass
        self.accept()
        app = self.window()
        app.close()
        try:
            QApplication.quit()
            sys.exit(0)
        except SystemExit:
            pass