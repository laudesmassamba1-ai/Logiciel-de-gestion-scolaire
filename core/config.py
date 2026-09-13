import os
import sys
import threading
from pathlib import Path

from resources.design_tokens import Radius as _R


APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.6.0"

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"


APP_FONT_FAMILY = "Inter"
APP_FONT_FALLBACK = ("Segoe UI", "Calibri", "Lato", "DejaVu Sans", "Noto Sans", "Arial", "sans-serif")
APP_FONT_SIZE = 11


import os as _os
API_BASE_URL = _os.environ.get("GS_API_URL", "http://127.0.0.1:8000")
API_TIMEOUT = float(_os.environ.get("GS_API_TIMEOUT", "2.0"))
SYNC_ACTIVE = _os.environ.get("GS_SYNC_ACTIVE", "false").lower() in ("true", "1", "yes")


PAYS_DEFAUT = "Republique du Congo"
VILLE_DEFAUT = "Brazzaville"
INDICATIF_TEL = "+242"
DEVISE = "FCFA"


C_TEXT = "#1D1D1F"
C_TEXT_SECONDARY = "#3A3A40"
C_TEXT_MUTED = "#6E6E73"
C_TEXT_LIGHT = "#8A8A93"
C_EMPTY_STATE = "#5B5B64"

C_GOLD = "#C8960C"
C_GOLD_HOVER = "#DAA520"
C_GOLD_PRESSED = "#A67B0A"
C_GOLD_LIGHT = "#FEF3C7"
C_GOLD_BG = "#FFFBEB"
C_GOLD_BORDER = "#FDE68A"

C_BLUE = "#1E40AF"
C_BLUE_LIGHT = "#EFF6FF"
C_BLUE_BORDER = "#BFDBFE"

C_RED = "#B91C1C"
C_RED_BG = "#FEF2F2"
C_RED_BORDER = "#FECACA"

# --- Theme « Pastel 95 » (suite VIII, 2026-09-09) -------------------------
# Un « Windows 95 leger » : fond desktop gris-bleu froid, panneaux relevés
# (bevel clair en haut, pied plus sombre en bas), adouci par des cartes
# rondes et un seul accent or. Sérieux mais vivant : ombres « cartoon »
# discrètes au lieu de barres dures.
C_BG = "#E7EBF3"
C_BG_ALT = "#DBE1EB"
C_CARD = "#FFFFFF"
C_BORDER = "#DAE0EA"
C_BORDER_STRONG = "#C4CCDA"
C_BEV_LIGHT = "#FFFFFF"
C_BEV_DARK = "#C2CBD8"

C_INK = "#20202A"
C_INK_2 = "#2C3342"
C_SIDEBAR_TEXT = "#3E4451"
C_SIDEBAR_MUTED = "#99A2B2"
C_SIDEBAR_HOVER = "#FFFFFF"
C_SIDEBAR_ACTIVE = "#FFFAEB"
C_SIDEBAR_ACTIVE_TEXT = "#8A6410"
C_BG_SOFT = "#F6F8FB"
C_SHADOW = "46, 60, 80"
C_FOCUS_RING = "#C8960C"
C_GRAD_TOP = "#F0BC45"
C_GRAD_BOTTOM = "#C28C0C"

C_SUCCESS = C_GOLD
C_SUCCESS_DARK = C_GOLD_PRESSED
C_DANGER = C_RED
C_DANGER_BG = C_RED_BG
C_DANGER_BORDER = C_RED_BORDER
C_WARNING = "#D97706"
C_INFO = C_BLUE

C_ACTION_BLUE = C_BLUE
C_ACTION_BLUE_LIGHT = C_BLUE_LIGHT
C_ACTION_BLUE_BORDER = C_BLUE_BORDER
C_PRIMARY = C_GOLD
C_PRIMARY_HOVER = C_GOLD_HOVER
C_PRIMARY_PRESSED = C_GOLD_PRESSED
C_PRIMARY_LIGHT = C_GOLD_LIGHT
C_PRIMARY_BG = C_GOLD_BG

# Boutons « 3D douce » : pied plus sombre de 2px qui s'appuie au clic.
_STOP_SOL = f"stop:0 {C_GRAD_TOP}, stop:0.55 #DEA821, stop:1 {C_GRAD_BOTTOM}"

STYLE_BTN_PRIMARY = (
    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" {_STOP_SOL}); color: #FFFFFF; border: none;"
    " border: 2px solid #A17608; border-radius: 12px;"
    " padding: 9px 18px; font-weight: 700; font-size: 13px; }"
    " QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #FFCE63, stop:0.55 #E6AC26, stop:1 #D09A0F);"
    " border: 2px solid #A17608; }"
    " QPushButton:pressed { border: 2px solid #805F06;"
    " padding: 10px 18px 8px 18px; }"
    " QPushButton:disabled { background: #E6EAF1; color: #A3ADBF;"
    " border: 2px solid #CBD3E0; }"
)
STYLE_BTN_SECONDARY = (
    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #FFFFFF, stop:0.6 #F4F6FA, stop:1 #E8ECF3);"
    " color: #272E42; border: 1px solid #C6CEDB;"
    " border: 2px solid #C6CEDB; border-radius: 12px;"
    " padding: 9px 18px; font-weight: 600; font-size: 13px; }"
    " QPushButton:hover { background: #FFFFFF; border-color: #AEB9C9; }"
    " QPushButton:pressed { border: 2px solid #A8B2C2;"
    " padding: 10px 18px 8px 18px; }"
    " QPushButton:disabled { color: #A3ADBF; background: #ECF0F5; }"
)
STYLE_BTN_SUCCESS = (
    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" {_STOP_SOL}); color: #FFFFFF; border: none;"
    " border: 2px solid #A17608; border-radius: 12px;"
    " padding: 9px 18px; font-weight: 700; font-size: 13px; }"
    " QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #FFCE63, stop:0.55 #E6AC26, stop:1 #D09A0F); }"
    " QPushButton:pressed { border: 2px solid #805F06;"
    " padding: 10px 18px 8px 18px; }"
)
STYLE_BTN_DANGER = (
    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #FFF3F3, stop:0.6 #FDE8E8, stop:1 #F7D9D9);"
    " color: #B91C1C; border: 1px solid #F3C4C4;"
    " border: 2px solid #E8ABB0; border-radius: 12px;"
    " padding: 9px 18px; font-weight: 700; font-size: 13px; }"
    " QPushButton:hover { background: #FDE1E1; }"
    " QPushButton:pressed { border: 2px solid #DFA0A6;"
    " padding: 10px 18px 8px 18px; }"
)
STYLE_BTN_ADD = (
    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #FFF7E0, stop:0.6 #FDEECC, stop:1 #F9E3AC);"
    " color: #6B4B04; border: 1px solid #EED28A;"
    " border: 2px solid #DFBE6E; border-radius: 12px;"
    " padding: 9px 18px; font-weight: 700; font-size: 13px; }"
    " QPushButton:hover { background: #FFF2CF; }"
    " QPushButton:pressed { border: 2px solid #D5B464;"
    " padding: 10px 18px 8px 18px; }"
)
STYLE_CARD = (
    f"background: {C_CARD}; border: 1px solid #E1E6EF;"
    f" border: 1px solid #D3DAE6;"
    f" border-radius: 14px; padding: 14px;"
)
STYLE_SELECTOR = (
    f"background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border: 2px solid #D3DAE6; border-radius: 12px; padding: 8px 14px;"
)

# Parametres : boites de groupe, labels, images et petits boutons.
STYLE_GROUP_BOX = (
    f"QGroupBox {{ font-weight: 700; color: {C_TEXT};"
    f" border: 1px solid {C_BORDER}; border-radius: 12px;"
    f" padding: 4px 10px; margin-top: 6px; }}"
)
STYLE_HELP_MUTED = f"color: {C_TEXT_MUTED}; font-size: 12px; border: none;"
STYLE_LABEL_BOLD_MUTED = (
    f"font-weight: bold; color: {C_TEXT_MUTED}; font-size: 11px; border: none;")
STYLE_IMAGE_PLACEHOLDER = (
    f"border: 2px dashed {C_BORDER}; border-radius: 12px; background: {C_BG_ALT};")
STYLE_LIST_CARD = (
    f"QListWidget {{ border: 2px solid {C_BORDER}; border-radius: 12px;"
    f" background: {C_BG_ALT}; }}"
)
STYLE_BTN_MINI_DANGER = (
    f"QPushButton {{ background: {C_RED_BG}; color: {C_RED};"
    f" border: 1px solid {C_RED_BORDER}; border-radius: 12px;"
    f" font-size: 12px; font-weight: bold; }}"
)
STYLE_BTN_ADD_SMALL = (
    f"QPushButton {{ background: {C_GOLD_BG}; color: {C_GOLD_PRESSED};"
    f" border: 1px solid {C_GOLD_BORDER}; border-radius: 12px;"
    f" padding: 6px 14px; font-weight: 600; font-size: 12px; }}"
)

# Auth : embleme rond, bouton principal et libelles de champs.
STYLE_AUTH_EMBLEME = (
    f"QLabel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" {_STOP_SOL}); color: #FFFFFF; font-size: 24px; font-weight: 800;"
    " border: 4px solid #9A7007; border-radius: 36px; }"
)
STYLE_AUTH_BTN = (
    f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" {_STOP_SOL}); color: #FFFFFF; border: 3px solid #9A7007;"
    " border-radius: 12px; padding: 11px 20px;"
    " font-size: 14px; font-weight: 800; }"
    "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #FFCE63, stop:0.55 #E6AC26, stop:1 #D09A0F); }"
    "QPushButton:pressed { border: 3px solid #805F06;"
    " padding: 12px 20px 10px 20px; }"
    "QPushButton:disabled { background: #E6EAF1; color: #A3ADBF;"
    " border: 3px solid #CBD3E0; }"
)
STYLE_AUTH_FIELD_LABEL = (
    f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: 700;"
)

# Coquille principale : entete, recherche, chip app, badge d'etat API.
STYLE_ENTETE = (
    "QFrame#pageEntete { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #FFFFFF, stop:1 #F7F9FC);"
    " border-bottom: 1px solid #D3DAE6; }"
)
STYLE_ENTETE_TITRE = (
    f"color: {C_INK}; font-size: 13px; font-weight: 700; letter-spacing: 0.4px;"
)
STYLE_ENTETE_DATE = "color: #8A8A93; font-size: 12px; font-weight: 500;"
STYLE_RECHERCHE = (
    "QLineEdit { background: #F1F4F9; border: 2px solid #C9D2DF;"
    " border-radius: 12px; padding: 6px 14px; font-size: 12px;"
    " color: #20202A; }"
    "QLineEdit:focus { background: #FFFFFF;"
    f" border: 2px solid {C_GOLD}; border-radius: 12px; }}"
)
STYLE_CHIP_APP = (
    f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
    f" stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM});"
    " color: #FFFFFF; font-weight: 800; font-size: 10px;"
    " letter-spacing: 1px; padding: 4px 12px; border-radius: 12px;"
)
STYLE_NAV_ASSISTANT = (
    "QPushButton { color: #8A6410; text-align: left; padding: 8px 12px;"
    " border: 1px solid transparent; margin: 1px 10px; border-radius: 12px;"
    " font-size: 13px; font-weight: 700; background: #FBF2DF; }"
    "QPushButton:hover { background-color: #F0E6CE; color: #8A6410;"
    f" border: 1px solid {C_GOLD}; }}"
    "QPushButton:pressed { background-color: #EADFC2; }"
)
STYLE_BADGE_API = (
    "padding: 3px 12px; border-radius: 12px; font-weight: 700;"
    " font-size: 11px; border: 1px solid transparent;"
)

STYLE_HEADER_TITLE = f"font-size: 20px; font-weight: 700; color: {C_TEXT}; margin: 0;"
STYLE_HEADER_SUBTITLE = f"font-size: 13px; color: {C_TEXT_MUTED}; margin: 0 0 4px 0;"
STYLE_EMPTY_STATE = f"color: {C_EMPTY_STATE}; font-size: 14px; padding: 40px;"
STYLE_STATUS = f"color: {C_TEXT_MUTED}; font-size: 12px; padding: 4px;"

STYLE_SCROLL = "QScrollArea { border: none; background: transparent; }"

STYLE_CHART_CARD = (
    f"QFrame {{ background: {C_CARD}; border: 1px solid {C_BORDER};"
    " border-radius: 12px; }"
)

STYLE_TABLE = (
    f"QTableWidget {{ background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: 14px; gridline-color: transparent; font-size: 13px;"
    f" alternate-background-color: #F5F8FC; }}"
    f"QTableWidget::item {{ padding: 5px 8px; border-bottom: 1px solid #EDF0F6; }}"
    f"QTableWidget::item:selected {{ background: #FDF3D8; color: #7A5A0F; }}"
    f"QTableWidget::item:hover {{ background: #FBF4E2; }}"
    f"QHeaderView::section {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #F0F3F8, stop:1 #E2E8F1); color: {C_TEXT_MUTED};"
    f" font-weight: 700; font-size: 11px; padding: 9px 10px;"
    f" border: none; border-right: 1px solid #E0E6EF;"
    f" border-bottom: 2px solid #C2CBD8; }}"
    f"QHeaderView::section:last {{ border-right: none; }}"
    f"QTableCornerButton::section {{ background: #E2E8F1; border: none; }}"
)


APP_STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    font-family: 'Inter', 'Segoe UI', 'Lato', 'DejaVu Sans', sans-serif;
    font-size: 11pt; color: {C_TEXT};
}}
QMainWindow, QDialog {{ background-color: {C_BG}; }}

QSplitter::handle {{ background: {C_BG}; border: none; }}
QSplitter::handle:hover {{ background: {C_BORDER_STRONG}; }}
QSplitter::handle:horizontal {{ width: 6px; }}
QSplitter::handle:vertical {{ height: 6px; }}

QToolTip {{
    background-color: {C_INK}; color: #F2F4F8;
    padding: 6px 11px; border-radius: {_R.SM}px; font-size: 12px;
    border: 1px solid {C_INK_2};
}}

QPushButton {{
    background-color: {C_CARD}; color: {C_TEXT_SECONDARY};
    border: 2px solid #B4BDCC;
    border-radius: {_R.MD}px; padding: 8px 18px; font-weight: 600; font-size: 13px;
}}
QPushButton:hover {{ background-color: {C_PRIMARY_BG}; border-color: {C_PRIMARY}; }}
QPushButton:pressed {{ border: 2px solid #A8B2C2; }}
QPushButton:default {{ background-color: {C_PRIMARY}; color: #FFFFFF;
    border: 2px solid {C_GOLD_PRESSED}; font-weight: 700; }}
QPushButton:default:hover {{ background-color: {C_PRIMARY_HOVER}; }}
QPushButton:disabled {{ background-color: #EAEEF4; color: {C_TEXT_MUTED}; border-color: #D3DAE6; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 3px; }}
QScrollBar::handle:vertical {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #CBD3E0, stop:1 #B9C2D2); border-radius: 5px; min-height: 30px;
    border: 1px solid #AEB8C9; }}
QScrollBar::handle:vertical:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #D9A91F, stop:1 {C_GOLD_PRESSED}); }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 3px; }}
QScrollBar::handle:horizontal {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #CBD3E0, stop:1 #B9C2D2); border-radius: 5px; min-width: 30px;
    border: 1px solid #AEB8C9; }}
QScrollBar::handle:horizontal:hover {{ background: {C_GOLD_PRESSED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

{STYLE_TABLE}

QMenu {{
    background-color: {C_CARD}; border: 2px solid #C7CFDD; border-radius: {_R.LG}px; padding: 5px;
}}
QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: {_R.SM}px; color: {C_TEXT_SECONDARY}; }}
QMenu::item:selected {{ background-color: {C_PRIMARY}; color: #FFFFFF; font-weight: 700; }}

QStatusBar {{
    background: {C_CARD}; color: {C_TEXT_MUTED};
    border-top: 1px solid #D8DEE9; font-size: 12px;
}}
QMessageBox QPushButton, QDialog QPushButton {{
    min-height: 36px; padding: 8px 22px; border-radius: {_R.MD}px;
}}

QListWidget {{
    background: transparent; border: none;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: {_R.SM}px; color: {C_TEXT_SECONDARY}; }}
QListWidget::item:hover {{ background-color: #FBF4E2; }}
QListWidget::item:selected {{ background-color: {C_PRIMARY_LIGHT}; color: {C_SIDEBAR_ACTIVE_TEXT}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    border: 2px solid #C4CCDA;
    border-radius: {_R.MD}px; padding: 7px 12px;
    background-color: {C_CARD}; color: {C_TEXT}; font-size: 13px;
    selection-background-color: {C_PRIMARY_LIGHT};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
    border: 2px solid {C_TEXT_MUTED};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 2px solid {C_FOCUS_RING};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QDateEdit:disabled, QTextEdit:disabled {{
    background-color: {C_BG_ALT}; color: {C_TEXT_MUTED}; border: 2px solid {C_BORDER};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{
    image: none; border-left: 5px solid transparent;
    border-right: 5px solid transparent; border-top: 6px solid {C_TEXT_MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: {_R.MD}px;
    selection-background-color: {C_PRIMARY}; selection-color: #FFFFFF;
    padding: 4px; color: {C_TEXT_SECONDARY};
}}

QCheckBox {{ spacing: 8px; color: {C_TEXT_SECONDARY}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border: 2px solid #C4CCDA;
    border-radius: {_R.SM}px; background: {C_CARD};
}}
QCheckBox::indicator:hover {{ border-color: {C_PRIMARY}; }}
QCheckBox::indicator:checked {{
    background-color: {C_PRIMARY}; border-color: {C_PRIMARY_PRESSED};
}}

QGroupBox {{
    background: {C_CARD}; border: 1px solid #C7CFDD; border-radius: {_R.MD}px;
    margin-top: 10px; padding: 6px 10px; font-weight: 700;
    font-size: 13px; color: {C_TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 14px; top: 2px; padding: 0 8px;
    background: {C_BG}; color: {C_TEXT_MUTED};
}}

QTabWidget::pane {{ border: none; background: transparent; top: 0; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {C_TEXT_MUTED}; padding: 8px 16px 10px 16px;
    border: none; border-bottom: 2px solid transparent; margin-right: 6px;
    font-weight: 600; font-size: 13px;
}}
QTabBar::tab:hover {{ color: {C_PRIMARY_PRESSED}; border-bottom: 2px solid {C_GOLD_BORDER}; }}
QTabBar::tab:selected {{
    color: {C_PRIMARY_PRESSED}; font-weight: 700;
    border-bottom: 2px solid {C_PRIMARY};
}}

QLabel {{ color: {C_TEXT_SECONDARY}; }}

QCalendarWidget QWidget {{ alternate-background-color: #FBF4E2; }}
"""


QSS_SIDEBAR = f"""
QPushButton {{
    color: {C_SIDEBAR_TEXT};
    border-radius: {_R.MD}px; font-size: 13px; font-weight: 600; background: transparent;
    text-align: left; padding: 9px 13px; border: none;
}}
QPushButton:hover {{
    background-color: {C_SIDEBAR_HOVER};
    border: 2px solid #C2CBD8;
}}
QPushButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #F6C23E, stop:0.6 #DEA821, stop:1 #C28C0C);
    color: #3F2B02; font-weight: 700;
    border: 2px solid #9A7007;
    border-radius: {_R.MD}px;
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
    SYNC_ACTIVE = bool(_cfg_fichier["sync_active"])
if "GS_API_URL" not in os.environ and _cfg_fichier.get("api_url"):
    API_BASE_URL = str(_cfg_fichier["api_url"])

# Indique si ce poste doit lancer le serveur automatiquement au demarrage.
# Sur le poste hote, api_url pointe vers 127.0.0.1 (ou localhost).
SERVEUR_AUTO = _cfg_fichier.get("serveur_auto", False) if "GS_SERVEUR_AUTO" not in os.environ else \
    os.environ.get("GS_SERVEUR_AUTO", "false").lower() in ("true", "1", "yes")


def est_hote() -> bool:
    """Retourne True si ce poste est configure comme serveur (hôte)."""
    return "127.0.0.1" in API_BASE_URL or "localhost" in API_BASE_URL


UI_DIR = resource_path("ui/ui_files")
DB_PATH = data_dir() / "ecole.db"
DOCS_DIR = data_dir() / "documents"


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
