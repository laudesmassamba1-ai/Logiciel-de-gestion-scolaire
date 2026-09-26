import os
import sys
import threading
from pathlib import Path

from resources.design_tokens import Radius as _R


APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.6.5"

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return PROJECT_ROOT / relative


def data_dir() -> Path:
    override = os.environ.get("GS_DATA_DIR")
    if override:
        folder = Path(override) / "data"
    elif hasattr(sys, "_MEIPASS"):
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", str(Path.home()))) / "GestionScolaire"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "GestionScolaire"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "gestion-scolaire"
        folder = base / "data"
    else:
        folder = PROJECT_ROOT / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


APP_FONT_FAMILY = "Inter"
APP_FONT_FALLBACK = ("Segoe UI", "Calibri", "Lato", "DejaVu Sans", "Noto Sans", "Arial", "sans-serif")
APP_FONT_SIZE = 11
FONT_DISPLAY_FAMILY = "Inter Display"
# Police de repli pour les pictos/emojis (badges, onglets, boutons-icones) :
# les polices standard n'ont AUCUN glyphe emoji (verifie par inFontUcs4),
# Noto Color Emoji est present sur le systeme et doit figurer dans chaque
# liste font-family sous peine de carres vides.
FONT_EMOJI = "'Noto Color Emoji'"


import os as _os
API_BASE_URL = _os.environ.get("GS_API_URL", "http://127.0.0.1:8000")
API_TIMEOUT = float(_os.environ.get("GS_API_TIMEOUT", "2.0"))
SYNC_ACTIVE = _os.environ.get("GS_SYNC_ACTIVE", "false").lower() in ("true", "1", "yes")


PAYS_DEFAUT = "Republique du Congo"
VILLE_DEFAUT = "Brazzaville"
INDICATIF_TEL = "+242"
DEVISE = "FCFA"

# --- Charo IA locale v2 (voir docs/PROJET_CHARO_IA_LOCALE.md) --------------
# Chaque palier est branche derriere un interrupteur : le passage v1/v2 se
# fait sans deploiement ni redemarrage, et un palier douteux se desactive
# immediatement. Les seuils restent lisibles pour etre ajustes sans code.
CHARO_V2 = {
    # P1 : routeur d'intentions declaratif (remplace l'ordre fixe des
    # handlers metier, avec repli automatique sur l'ancien ordre).
    "ROUTEUR": _os.environ.get("GS_CHARO_ROUTEUR", "true").lower() in (
        "true", "1", "yes"),
    # Seuil de retention d'une intention (module intentions.py).
    "SEUIL_INTENTION": float(_os.environ.get("GS_CHARO_SEUIL_INTENTION", "0.45")),
    # Au-dela, on court-circuite les handlers de priorite superieure.
    "SEUIL_CONFIANT": float(_os.environ.get("GS_CHARO_SEUIL_CONFIANT", "0.80")),
}

# Modes de reglement acceptes par l'etablissement (source unique) :
# partage entre la caisse, les paiements et le dossier d'inscription.
MODES_PAIEMENT = ("Especes", "Mobile Money (MTN / Airtel)",
                  "Cheque / Virement")
MODES_SORTIE = ("Especes", "Virement", "Cheque")


# --- Theme « Liquid Glass clair » (refonte Session, 2026)
# Fond aurora (bleu glace -> lavande -> ambre) porte par APP_STYLESHEET,
# cartes en verre (blanc, hairline glacee, coins uniformes), accent moderne
# bleu -> violet en degrade signature, or conserve comme marque d'ecole.

C_TEXT = "#1E2430"
C_TEXT_SECONDARY = "#465064"
C_TEXT_MUTED = "#667086"
C_TEXT_LIGHT = "#8C96AB"
C_EMPTY_STATE = "#59647A"

C_GOLD = "#C8960C"
C_GOLD_HOVER = "#B7820A"
C_GOLD_PRESSED = "#A67409"
C_GOLD_LIGHT = "#F6EED7"
C_GOLD_BG = "#FBF7EC"
C_GOLD_BORDER = "#E9DFC4"
C_GOLD_GRAD_TOP = "#E0A81E"
C_GOLD_GRAD_BOTTOM = "#B8860B"

C_BLUE = "#4F6DF5"
C_BLUE_HOVER = "#3D59E0"
C_BLUE_PRESSED = "#3350D0"
C_BLUE_LIGHT = "#E8EDFE"
C_BLUE_BORDER = "#CDD9FD"
C_ACCENT_VIOLET = "#8B5CF6"
C_VIOLET_HOVER = "#7A4DF0"
C_VIOLET_PRESSED = "#6A3FE0"
C_VIOLET_LIGHT = "#F0EBFF"
C_VIOLET_BORDER = "#DDD2FC"

C_RED = "#E5484D"
C_RED_HOVER = "#D7353A"
C_RED_PRESSED = "#C2282E"
C_RED_BG = "#FFECEE"
C_RED_BORDER = "#F8D3D6"

C_GREEN = "#12A45B"
C_GREEN_DARK = "#0E8A4C"
C_GREEN_BG = "#E7F8EF"
C_GREEN_BORDER = "#CDEDDA"

C_WARN_BG = "#FFF4E5"
C_WARN_TEXT = "#A9621A"

C_WARNING = "#D9822B"
C_WARNING_HOVER = "#C26F1E"
C_WARNING_PRESSED = "#A85E16"
C_WARNING_BG = "#FFF4E5"
C_WARNING_TEXT = "#A9621A"

C_INFO = C_BLUE
C_INFO_BG = "#EDF2FF"
C_INFO_BORDER = "#CDD9FD"

C_GRID = "#C9D4E6"  # lignes de separation des tableaux (net, lisible)

# --- Theme « Liquid Glass » ---------------------------------------------
C_BG = "#F3F6FC"
C_BG_ALT = "#EDF2FB"
C_CARD = "#FFFFFF"
C_BORDER = "#E2E9F5"
C_BORDER_STRONG = "#C3CFE2"
C_CONTOUR = "#4A5568"  # contour net des sections (boutons, cartes, tables)
C_BEV_LIGHT = "#FFFFFF"
C_BEV_DARK = "#D6DFED"

C_INK = "#1E2430"
C_INK_2 = "#465064"
C_SIDEBAR_TEXT = "#465064"
C_SIDEBAR_MUTED = "#8C96AB"
C_SIDEBAR_HOVER = "#EDF2FB"
C_SIDEBAR_ACTIVE = "#E7ECFE"
C_SIDEBAR_ACTIVE_TEXT = "#3A52D8"
C_BG_SOFT = "#F0F4FC"
C_SHADOW = "36, 52, 100"
C_FOCUS_RING = "#4F6DF5"
C_GRAD_TOP = "#5B7BF7"
C_GRAD_BOTTOM = "#7C5CF0"

# --- Tailles pilotables par le configurateur graphique (theme_config.json) ---
T_TAILLE_TITRE_PAGE = 26
T_TAILLE_SOUS_TITRE = 14
# Boutons
T_RAYON_BTN = 12
T_PAD_BTN_Y = 9
T_PAD_BTN_X = 18
# Champs de saisie / selecteurs
T_RAYON_CHAMP = 12
T_PAD_CHAMP_Y = 7
T_PAD_CHAMP_X = 13
# Cartes et fenetres
T_RAYON_CARTE = 16
T_PAD_CARTE = 16
# Tableaux
T_RAYON_TABLE = 14
T_TABLE_FONT = 13
T_TABLE_PAD_Y = 9
T_TABLE_PAD_X = 12
T_TABLE_HEADER_FONT = 11
T_TABLE_HEADER_PAD_Y = 11
T_TABLE_HEADER_PAD_X = 12
# KPI et sidebar
T_KPI_HAUTEUR = 112
T_SIDEBAR_LARGEUR = 240

C_SUCCESS = C_GREEN
C_SUCCESS_DARK = "#0E8A4C"
C_DANGER = C_RED
C_DANGER_BG = C_RED_BG
C_DANGER_BORDER = C_RED_BORDER

C_ACTION_BLUE = C_BLUE
C_ACTION_BLUE_LIGHT = C_BLUE_LIGHT
C_ACTION_BLUE_BORDER = C_BLUE_BORDER
C_PRIMARY = C_BLUE
C_PRIMARY_HOVER = C_BLUE_HOVER
C_PRIMARY_PRESSED = C_BLUE_PRESSED
C_PRIMARY_LIGHT = C_BLUE_LIGHT
C_PRIMARY_BG = "#F1F4FF"
C_PRIMARY_BORDER = "#CDD9FD"

# --- Theme personnalise ------------------------------------------------
# Le configurateur graphique ecrit `data/theme_config.json`. Il est relu ici,
# APRES la definition des aliases (C_PRIMARY = C_BLUE... pointent donc vers
# les valeurs deja surchargees) et avant tous les styles STYLE_*/APP_STYLESHEET :
# les f-strings s'evaluent avec les couleurs/tailles FINALES. Le module
# `resources.design_tokens` (importe en tete) applique deja les memes valeurs
# a ses propres classes (sources jumelles).
_CHEMIN_THEME = data_dir() / "theme_config.json"
_theme_brut = {}
if _CHEMIN_THEME.exists():
    try:
        import json as _json_theme
        _theme_brut = _json_theme.loads(_CHEMIN_THEME.read_text(encoding="utf-8"))
        if isinstance(_theme_brut, dict):
            # Couleurs : surcharge directe des constantes C_* existantes.
            _nouveaux = {}
            for _cle, _val in _theme_brut.get("couleurs", {}).items():
                if _cle in globals() and isinstance(_val, str) and _val.startswith("#"):
                    _nouveaux[_cle] = _val
            globals().update(_nouveaux)
            # Polices (corps / titres-display).
            _typo_theme = _theme_brut.get("typo", {})
            if isinstance(_typo_theme.get("police_corps"), str) and _typo_theme["police_corps"]:
                globals()["APP_FONT_FAMILY"] = _typo_theme["police_corps"]
            if isinstance(_typo_theme.get("police_titres"), str) and _typo_theme["police_titres"]:
                globals()["FONT_DISPLAY_FAMILY"] = _typo_theme["police_titres"]
            # Dimensions pilotables : chaque cle JSON conduit a une variable
            # T_* du module (les STYLE_* ci-dessous les lisent).
            _dims_theme = {k: int(v) for k, v in _theme_brut.get("dimensions", {}).items()
                           if isinstance(v, (int, float)) and v > 0}
            _MAP_DIMS_VAR = {
                "taille_titre_page": "T_TAILLE_TITRE_PAGE",
                "taille_sous_titre": "T_TAILLE_SOUS_TITRE",
                "taille_corps": "T_TABLE_FONT",
                "rayon_btn": "T_RAYON_BTN",
                "pad_btn_y": "T_PAD_BTN_Y",
                "pad_btn_x": "T_PAD_BTN_X",
                "rayon_champ": "T_RAYON_CHAMP",
                "pad_champ_y": "T_PAD_CHAMP_Y",
                "pad_champ_x": "T_PAD_CHAMP_X",
                "rayon_carte": "T_RAYON_CARTE",
                "pad_carte": "T_PAD_CARTE",
                "rayon_table": "T_RAYON_TABLE",
                "table_font": "T_TABLE_FONT",
                "table_pad_y": "T_TABLE_PAD_Y",
                "table_pad_x": "T_TABLE_PAD_X",
                "table_header_font": "T_TABLE_HEADER_FONT",
                "table_header_pad_y": "T_TABLE_HEADER_PAD_Y",
                "table_header_pad_x": "T_TABLE_HEADER_PAD_X",
                "kpi_hauteur": "T_KPI_HAUTEUR",
                "sidebar_largeur": "T_SIDEBAR_LARGEUR",
            }
            for _cle_json, _var_cfg in _MAP_DIMS_VAR.items():
                if _cle_json in _dims_theme:
                    globals()[_var_cfg] = _dims_theme[_cle_json]
    except Exception:
        pass

# ------------------------------------------------------------
# Composants themables : reglages CIBLES par element de l'app
# (liste des eleves, emploi du temps, statuts financiers...).
# Chaque composant possede ses propres couleurs, stockees dans
# theme_config.json sous "composants" -> {nom: {cle: hex}}.
# ------------------------------------------------------------
_COMPOSANTS_DEFAUTS = {
    "eleves_table": {
        "grille": C_GRID,
        "fond_entete": C_BG_SOFT,
        "texte_entete": C_TEXT_SECONDARY,
        "fond_alternat": C_BG_SOFT,
        "bordure": C_CONTOUR,
    },
    "planning": {
        "grille": C_GRID,
        "fond_entete": C_BG_SOFT,
        "texte_entete": C_TEXT_SECONDARY,
        "fond_cellule": C_CARD,
        "fond_occupe": C_PRIMARY_LIGHT,
        "texte_occupe": C_SIDEBAR_ACTIVE_TEXT,
        "bordure": C_CONTOUR,
    },
    "statuts": {
        "paye": C_GREEN,
        "du": C_WARNING,
        "retard": C_RED,
        "present": C_GREEN,
        "absent": C_RED,
        "justifie": C_WARNING,
    },
    "statistiques": {
        "barres": C_ACCENT_VIOLET,
        "courbe": C_BLUE,
        "secteurs": C_VIOLET_LIGHT,
        "grille": C_EMPTY_STATE,
    },
}

_composants_theme = {}
if isinstance(_theme_brut, dict) and isinstance(_theme_brut.get("composants"), dict):
    _composants_theme = _theme_brut["composants"]

COMPOSANTS = {}
for _nom_comp, _defs_comp in _COMPOSANTS_DEFAUTS.items():
    _surch_comp = _composants_theme.get(_nom_comp) or {}
    COMPOSANTS[_nom_comp] = {
        _cle_comp: (_surch_comp[_cle_comp] if (
            isinstance(_surch_comp.get(_cle_comp), str)
            and _surch_comp[_cle_comp].startswith("#"))
            else _defs_comp[_cle_comp])
        for _cle_comp in _defs_comp
    }


def lire_composant(nom: str) -> dict:
    """Reglages couleurs d'un composant nomme (fallback : valeurs par defaut)."""
    return dict(COMPOSANTS.get(nom) or {})

# Boutons : accent moderne en degrade signature (bleu -> violet), etats
# sombres au survol/appui, or reserve a la marque d'ecole.

STYLE_BTN_PRIMARY = (
    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM}); color: #FFFFFF;"
    f" border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_BTN}px;"
    f" padding: {T_PAD_BTN_Y}px {T_PAD_BTN_X}px;"
    " font-weight: 600; font-size: 13px; }"
    f" QPushButton:hover {{ background: {C_PRIMARY_HOVER}; }}"
    f" QPushButton:pressed {{ background: {C_PRIMARY_PRESSED}; }}"
    " QPushButton:disabled { background: #E6EBF5; color: #A3ABC0; }"
)
STYLE_BTN_SECONDARY = (
    f"QPushButton {{ background: rgba(255,255,255,0.85); color: {C_TEXT_SECONDARY};"
    f" border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_BTN}px; padding: {T_PAD_BTN_Y}px {T_PAD_BTN_X}px;"
    " font-weight: 600; font-size: 13px; }"
    " QPushButton:hover { background: #F0F4FC; border-color: #3E4A5C; }"
    " QPushButton:pressed { background: #E4EBF6; border-color: #3E4A5C; }"
    " QPushButton:disabled { color: #A3ABC0; background: #F0F4FC;"
    " border-color: #D6DEEB; }"
)
STYLE_BTN_SUCCESS = (
    f"QPushButton {{ background: {C_GREEN}; color: #FFFFFF;"
    f" border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_BTN}px; padding: {T_PAD_BTN_Y}px {T_PAD_BTN_X}px;"
    " font-weight: 700; font-size: 13px; }"
    f" QPushButton:hover {{ background: {C_SUCCESS_DARK}; }}"
    f" QPushButton:pressed {{ background: #0C7A42; }}"
)
STYLE_BTN_DANGER = (
    f"QPushButton {{ background: {C_RED_BG}; color: {C_RED};"
    f" border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_BTN}px; padding: {T_PAD_BTN_Y}px {T_PAD_BTN_X}px;"
    " font-weight: 600; font-size: 13px; }"
    " QPushButton:hover { background: #FBDCDD; }"
    " QPushButton:pressed { background: #F7C9CB; }"
)
STYLE_BTN_ADD = (
    f"QPushButton {{ background: {C_BLUE_LIGHT}; color: #3A52D8;"
    f" border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_BTN}px; padding: {T_PAD_BTN_Y}px {T_PAD_BTN_X}px;"
    " font-weight: 600; font-size: 13px; }"
    " QPushButton:hover { background: #DCE4FD; }"
    " QPushButton:pressed { background: #CCD8FC; }"
)
STYLE_CARD = (
    f"background: {C_CARD}; border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_CARTE}px; padding: {T_PAD_CARTE}px;"
)
STYLE_SELECTOR = (
    f"background: {C_CARD}; border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_CHAMP}px; padding: {T_PAD_CHAMP_Y}px {T_PAD_CHAMP_X}px;"
)

# Parametres : boites de groupe, labels, images et petits boutons.
STYLE_GROUP_BOX = (
    f"QGroupBox {{ font-weight: 700; color: {C_TEXT};"
    f" border: 1px solid {C_CONTOUR}; border-radius: 12px;"
    f" padding: 4px 10px; margin-top: 6px; }}"
)
STYLE_HELP_MUTED = f"color: {C_TEXT_MUTED}; font-size: 12px; border: none;"
STYLE_LABEL_BOLD_MUTED = (
    f"font-weight: bold; color: {C_TEXT_MUTED}; font-size: 11px; border: none;")
STYLE_IMAGE_PLACEHOLDER = (
    f"border: 2px dashed {C_BORDER_STRONG}; border-radius: 12px; background: {C_BG_ALT};")
STYLE_LIST_CARD = (
    f"QListWidget {{ border: 1px solid {C_CONTOUR}; border-radius: 12px;"
    f" background: {C_BG_ALT}; }}"
)
STYLE_BTN_MINI_DANGER = (
    f"QPushButton {{ background: {C_RED_BG}; color: {C_RED};"
    f" border: 1px solid {C_CONTOUR}; border-radius: 8px;"
    f" font-size: 12px; font-weight: 600; }}"
)
STYLE_BTN_ADD_SMALL = (
    f"QPushButton {{ background: {C_BLUE_LIGHT}; color: #3A52D8;"
    f" border: 1px solid {C_CONTOUR}; border-radius: 8px;"
    f" padding: 6px 14px; font-weight: 600; font-size: 12px; }}"
)

# Auth : embleme rond (degrade or conserve pour la marque d'ecole) et
# bouton moderne en degrade signature.
STYLE_AUTH_EMBLEME = (
    f"QLabel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {C_GOLD_GRAD_TOP}, stop:1 {C_GOLD_GRAD_BOTTOM}); color: #FFFFFF;"
    " font-size: 26px; font-weight: 800;"
    " border: none; border-radius: 34px; }"
)
STYLE_AUTH_BTN = (
    f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM}); color: #FFFFFF;"
    f" border: 1px solid {C_CONTOUR}; border-radius: 12px; padding: 11px 20px;"
    " font-size: 14px; font-weight: 700; }"
    f"QPushButton:hover {{ background: {C_PRIMARY_HOVER}; }}"
    f"QPushButton:pressed {{ background: {C_PRIMARY_PRESSED}; }}"
    f"QPushButton:disabled {{ background: #E6EBF5; color: #A3ABC0; }}"
)
STYLE_AUTH_FIELD_LABEL = (
    f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: 600;"
)

# Coquille principale : entete verre, recherche, chip app, badge d'etat API.
STYLE_ENTETE = (
    f"QFrame#pageEntete {{ background: rgba(255,255,255,0.72);"
    f" border-bottom: 1px solid {C_CONTOUR}; }}"
)
STYLE_ENTETE_TITRE = (
    f"color: {C_INK}; font-size: 14px; font-weight: 700;"
)
STYLE_ENTETE_DATE = f"color: {C_TEXT_LIGHT}; font-size: 12px; font-weight: 500;"
STYLE_RECHERCHE = (
    f"QLineEdit {{ background: rgba(255,255,255,0.85); border: 1px solid {C_CONTOUR};"
    " border-radius: 10px; padding: 7px 14px; font-size: 12px;"
    f" color: {C_TEXT}; }}"
    "QLineEdit:focus { background: #FFFFFF;"
    f" border: 2px solid {C_FOCUS_RING}; }}"
)
STYLE_CHIP_APP = (
    f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
    f" stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM});"
    " color: #FFFFFF; font-weight: 700; font-size: 10px;"
    " letter-spacing: 0.6px; padding: 4px 12px; border-radius: 12px;"
    " border: none;"
)
STYLE_NAV_ASSISTANT = (
    f"QPushButton {{ color: {C_SIDEBAR_ACTIVE_TEXT}; text-align: left;"
    " padding: 8px 12px; border: none; margin: 1px 10px; border-radius: 10px;"
    " font-size: 13px; font-weight: 600;"
    f" background: {C_BLUE_LIGHT}; }}"
    f"QPushButton:hover {{ background-color: #DCE4FD;"
    f" color: {C_SIDEBAR_ACTIVE_TEXT}; border: none; }}"
    "QPushButton:pressed { background-color: #CCD8FC; }"
)
STYLE_BADGE_API = (
    "padding: 3px 12px; border-radius: 10px; font-weight: 600;"
    " font-size: 11px; border: 1px solid transparent;"
)

STYLE_HEADER_TITLE = (
    f"font-family: '{FONT_DISPLAY_FAMILY}', '{APP_FONT_FAMILY}', {FONT_EMOJI}, 'Segoe UI', sans-serif;"
    f" font-size: {T_TAILLE_TITRE_PAGE}px; font-weight: 800; letter-spacing: -0.4px;"
    f" color: {C_TEXT}; margin: 0;"
)
STYLE_HEADER_SUBTITLE = f"font-size: {T_TAILLE_SOUS_TITRE}px; color: {C_TEXT_MUTED}; margin: 0 0 4px 0;"
STYLE_EMPTY_STATE = f"color: {C_EMPTY_STATE}; font-size: 14px; padding: 40px;"
STYLE_STATUS = f"color: {C_TEXT_MUTED}; font-size: 12px; padding: 4px;"

STYLE_SCROLL = "QScrollArea { border: none; background: transparent; }"

STYLE_CHART_CARD = (
    f"QFrame {{ background: {C_CARD}; border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_CARTE}px; }}"
)

_STYLE_TABLE_HEADER = (
    f"QHeaderView::section {{ background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY};"
    f" font-family: '{APP_FONT_FAMILY}', {FONT_EMOJI}, 'Segoe UI', sans-serif; font-weight: 700;"
    f" font-size: {T_TABLE_HEADER_FONT}px; letter-spacing: 0.6px; text-transform: uppercase;"
    f" padding: {T_TABLE_HEADER_PAD_Y}px {T_TABLE_HEADER_PAD_X}px; border: none;"
    f" border-bottom: 2px solid {C_CONTOUR}; }}"
    f"QTableCornerButton::section {{ background: {C_BG_SOFT}; border: none; }}"
)
_STYLE_TABLE_ITEM = (
    f"QTableWidget::item {{ padding: {T_TABLE_PAD_Y}px {T_TABLE_PAD_X}px;"
    f" font-size: {T_TABLE_FONT}px;"
    f" border-bottom: 1px solid {C_GRID}; }}"
    f"QTableWidget::item:selected {{ background: {C_PRIMARY_LIGHT};"
    f" color: {C_SIDEBAR_ACTIVE_TEXT}; }}"
    f"QTableWidget::item:hover {{ background: {C_BG_ALT}; }}"
)

STYLE_TABLE = (
    f"QTableWidget {{ background: {C_CARD}; border: 1px solid {C_CONTOUR};"
    f" border-radius: {T_RAYON_TABLE}px; gridline-color: {C_GRID};"
    f" font-size: {T_TABLE_FONT}px;"
    f" alternate-background-color: {C_BG_SOFT}; }}"
    + _STYLE_TABLE_ITEM
    + _STYLE_TABLE_HEADER
)


# Fond aurora (bleu glace -> lavande -> ambre). Constante QSS reutilisable
# par toutes les fenetres qui posent un fond explicite (ne pas recopier le
# gradient a la main : c'est lui la source unique).
C_AURORA = (
    "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
    " stop:0 #EAF2FF, stop:0.45 #F2EEFF, stop:1 #FBF4E6);"
)

APP_STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    font-family: '{APP_FONT_FAMILY}', {FONT_EMOJI}, 'Segoe UI', 'Lato', 'DejaVu Sans', sans-serif;
    font-size: 11pt; color: {C_TEXT};
}}
QMainWindow, QDialog {{
    {C_AURORA}
}}

QSplitter::handle {{ background: transparent; border: none; }}
QSplitter::handle:hover {{ background: {C_BORDER_STRONG}; }}
QSplitter::handle:horizontal {{ width: 6px; }}
QSplitter::handle:vertical {{ height: 6px; }}

QToolTip {{
    background-color: {C_INK}; color: #FFFFFF;
    padding: 6px 11px; border-radius: {_R.SM}px; font-size: 12px;
    border: 1px solid rgba(255,255,255,0.12);
}}

QPushButton {{
    background-color: rgba(255,255,255,0.85); color: {C_TEXT_SECONDARY};
    border: 1px solid {C_CONTOUR};
    border-radius: {T_RAYON_BTN}px; padding: {T_PAD_BTN_Y}px {T_PAD_BTN_X}px;
    font-weight: 600; font-size: 13px;
}}
QPushButton:hover {{ background-color: #F0F4FC; border-color: #3E4A5C; }}
QPushButton:pressed {{ background-color: #E4EBF6; }}
QPushButton:default {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM}); color: #FFFFFF;
    border: 1px solid {C_CONTOUR}; font-weight: 700; }}
QPushButton:default:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 {C_PRIMARY_HOVER}, stop:1 {C_ACCENT_VIOLET}); }}
QPushButton:disabled {{ background-color: #F0F4FC; color: #A3ABC0;
    border-color: {C_BORDER}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #BAC6DC; border-radius: 5px;
    min-height: 30px; border: none; }}
QScrollBar::handle:vertical:hover {{ background: {C_PRIMARY_PRESSED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #BAC6DC; border-radius: 5px;
    min-width: 30px; border: none; }}
QScrollBar::handle:horizontal:hover {{ background: {C_PRIMARY_PRESSED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

{STYLE_TABLE}

QMenu {{
    background-color: rgba(255,255,255,0.96);
    border: 1px solid {C_CONTOUR}; border-radius: {_R.LG}px; padding: 6px;
}}
QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: {_R.SM}px;
    color: {C_TEXT_SECONDARY}; }}
QMenu::item:selected {{ background-color: {C_PRIMARY_LIGHT};
    color: {C_SIDEBAR_ACTIVE_TEXT}; font-weight: 700; }}

QStatusBar {{
    background: rgba(255,255,255,0.72); color: {C_TEXT_MUTED};
    border-top: 1px solid {C_BORDER}; font-size: 12px;
}}
QMessageBox QPushButton, QDialog QPushButton {{
    min-height: 36px; padding: {T_PAD_BTN_Y}px 22px; border-radius: {T_RAYON_BTN}px;
}}

QListWidget {{
    background: transparent; border: none;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: {_R.SM}px;
    color: {C_TEXT_SECONDARY}; }}
QListWidget::item:hover {{ background-color: {C_BG_SOFT}; border: 1px solid {C_BORDER_STRONG}; }}
QListWidget::item:selected {{ background-color: {C_PRIMARY_LIGHT};
    color: {C_SIDEBAR_ACTIVE_TEXT}; border: 1px solid {C_PRIMARY}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    border: 1px solid {C_CONTOUR};
    border-radius: {T_RAYON_CHAMP}px; min-height: 24px;
    padding: {T_PAD_CHAMP_Y}px {T_PAD_CHAMP_X}px;
    background-color: rgba(255,255,255,0.9); color: {C_TEXT}; font-size: {T_TABLE_FONT}px;
    selection-background-color: {C_PRIMARY_LIGHT};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
    border: 1px solid {C_CONTOUR};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 2px solid {C_FOCUS_RING}; padding: {T_PAD_CHAMP_Y - 1}px {T_PAD_CHAMP_X - 1}px;
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QDateEdit:disabled, QTextEdit:disabled {{
    background-color: {C_BG_ALT}; color: {C_TEXT_MUTED}; border: 1px solid {C_BORDER};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{
    image: none; border-left: 5px solid transparent;
    border-right: 5px solid transparent; border-top: 6px solid {C_TEXT_MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: {_R.MD}px;
    selection-background-color: {C_PRIMARY_LIGHT};
    selection-color: {C_SIDEBAR_ACTIVE_TEXT};
    padding: 4px; color: {C_TEXT_SECONDARY};
}}

QCheckBox {{ spacing: 8px; color: {C_TEXT_SECONDARY}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border: 1px solid {C_CONTOUR};
    border-radius: {_R.SM}px; background: rgba(255,255,255,0.9);
}}
QCheckBox::indicator:hover {{ border-color: {C_PRIMARY}; }}
QCheckBox::indicator:checked {{
    background-color: {C_PRIMARY}; border-color: {C_PRIMARY_PRESSED};
}}

QGroupBox {{
    background: rgba(255,255,255,0.8); border: 1px solid {C_CONTOUR};
    border-radius: {_R.MD}px;
    margin-top: 10px; padding: 6px 10px; font-weight: 700;
    font-size: 13px; color: {C_TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 14px; top: 2px; padding: 0 8px;
    background: transparent; color: {C_TEXT_MUTED};
}}

QTabWidget::pane {{ border: none; background: transparent; top: 0; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {C_TEXT_MUTED}; padding: 8px 16px 10px 16px;
    border: none; border-bottom: 2px solid transparent; margin-right: 6px;
    font-weight: 600; font-size: 13px;
}}
QTabBar::tab:hover {{ color: {C_PRIMARY_PRESSED};
    border-bottom: 2px solid {C_BLUE_BORDER}; }}
QTabBar::tab:selected {{
    color: {C_PRIMARY_PRESSED}; font-weight: 700;
    border-bottom: 2px solid {C_PRIMARY};
}}

QLabel {{ color: {C_TEXT_SECONDARY}; }}

QCalendarWidget QWidget {{ alternate-background-color: {C_PRIMARY_LIGHT}; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: rgba(255,255,255,0.9); border-bottom: 1px solid {C_BORDER};
}}
QCalendarWidget QToolButton {{
    color: {C_TEXT}; background-color: transparent;
    border: none; border-radius: {_R.SM}px; padding: 4px 10px; font-weight: 600;
}}
QCalendarWidget QToolButton:hover {{ background-color: {C_BG_SOFT}; }}
QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
QCalendarWidget QMenu {{ background-color: {C_CARD}; color: {C_TEXT}; }}
QCalendarWidget QSpinBox {{
    background-color: {C_CARD}; color: {C_TEXT};
    selection-background-color: {C_PRIMARY_LIGHT};
    selection-color: {C_SIDEBAR_ACTIVE_TEXT};
}}
QCalendarWidget QAbstractItemView:enabled {{
    background-color: {C_CARD}; color: {C_TEXT};
    gridline-color: {C_BORDER};
    selection-background-color: {C_PRIMARY}; selection-color: #FFFFFF;
    outline: none;
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {C_TEXT_LIGHT}; }}
QCalendarWidget QHeaderView::section {{
    background-color: {C_CARD}; color: {C_TEXT_MUTED};
    border: none; padding: 4px;
}}
"""


ROLES = ("directeur", "gestionnaire")

ROLE_LABELS = {
    "directeur": "Directeur",
    "gestionnaire": "Gestionnaire",
}


PERIODES = ("1er Trimestre", "2eme Trimestre", "3eme Trimestre")

JOURS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi")

CRENEAUX = (
    "07h30 - 08h20",
    "08h20 - 09h10",
    "09h10 - 10h00",
    "10h00 - 10h20 (Pause)",
    "10h20 - 11h10",
    "11h10 - 12h00",
    "12h00 - 13h30 (Pause dejeuner)",
    "13h30 - 14h20",
)


# ------------------------------------------------------------
# Reglages de synchronisation persistes (assistant graphique).
# Priorite : variable d'environnement GS_* > sync.json > defauts.
# ------------------------------------------------------------

def fichier_config_sync() -> Path:
    return data_dir() / "sync.json"


_VERROU_CONFIG = threading.Lock()


def lire_config_sync() -> dict:
    import json
    try:
        return json.loads(fichier_config_sync().read_text(encoding="utf-8"))
    except Exception:
        return {}


def ecrire_config_sync(**valeurs) -> None:
    """Ecriture atomique (fichier temporaire + rename) et protegee par
    verrou : le thread d'auto-demarrage et l'interface peuvent ecrire en
    parallele sans perdre d'update ni produire un fichier tronque."""
    import json
    import os
    fichier = fichier_config_sync()
    tmp = fichier.with_suffix(".json.tmp")
    with _VERROU_CONFIG:
        cfg = lire_config_sync()
        cfg.update(valeurs)
        tmp.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, fichier)


_cfg_fichier = lire_config_sync()
if "GS_SYNC_ACTIVE" not in os.environ and "sync_active" in _cfg_fichier:
    SYNC_ACTIVE = str(_cfg_fichier["sync_active"]).lower() in ("true", "1", "yes")
if "GS_API_URL" not in os.environ and _cfg_fichier.get("api_url"):
    API_BASE_URL = str(_cfg_fichier["api_url"])

# Indique si ce poste doit lancer le serveur automatiquement au demarrage.
# Sur le poste hote, api_url pointe vers 127.0.0.1 (ou localhost).
SERVEUR_AUTO = _cfg_fichier.get("serveur_auto", False) if "GS_SERVEUR_AUTO" not in os.environ else \
    os.environ.get("GS_SERVEUR_AUTO", "false").lower() in ("true", "1", "yes")


def est_hote() -> bool:
    """Retourne True si ce poste est configure comme serveur (hôte)."""
    return "127.0.0.1" in API_BASE_URL or "localhost" in API_BASE_URL


def code_ecole() -> str:
    """Code identifiant de CETTE ecole (cloisonnement entre etablissements).

    Meme logiciel, mais chaque ecole a son propre code : un poste ne se
    synchronise qu'avec le serveur qui porte le meme code. Lu dynamiquement
    dans sync.json (le directeur peut le definir/regenerer)."""
    return str(lire_config_sync().get("code_ecole", "") or "").strip()


UI_DIR = resource_path("ui/ui_files")
DB_PATH = data_dir() / "ecole.db"
DOCS_DIR = data_dir() / "documents"


def assurer_ressource(nom: str, dossier_dest: str = "data") -> "Path":
    """Garantit la presence d'un fichier de donnees utilise par l'app.

    En execution depuis les sources, les fichiers vivent deja dans
    `data_dir()` (PROJECT_ROOT/data). En exécutable PyInstaller, les
    ressources « seed » (alarm.wav, etc.) sont embarquees dans le bundle
    (sys._MEIPASS) : au premier lancement on les copie dans `data_dir()`
    pour qu'elles survivent aux mises a jour et restent modifiables.

    Retourne toujours un chemin valide : le fichier local s'il existe,
    sinon le chemin embarqué (lecture), sinon le chemin local attendu.
    """
    local = data_dir() / nom
    if local.exists():
        return local
    embarquee = resource_path(dossier_dest) / nom
    try:
        import shutil
        if embarquee.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(embarquee), str(local))
            return local
    except OSError:
        pass
    return local if embarquee.exists() else local


DEFAULT_MATIERES = (
    "Francais",
    "Mathematiques",
    "Anglais",
    "Histoire-Geographie",
    "SVT",
    "Physique-Chimie",
    "Education Civique",
    "Informatique",
)

# Le dossier doit exister des le demarrage (base, sauvegardes...) mais un
# echec ici ne doit pas empecher l'import du module : db.connect() retente.
try:
    os.makedirs(data_dir(), exist_ok=True)
except OSError as exc:
    print(f"Avertissement : dossier de donnees indisponible ({exc})")
