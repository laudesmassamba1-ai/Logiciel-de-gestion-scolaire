import os
import sys
from pathlib import Path


APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.5.0"

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


C_TEXT = "#000000"
C_TEXT_SECONDARY = "#111111"
C_TEXT_MUTED = "#333333"
C_TEXT_LIGHT = "#555555"
C_EMPTY_STATE = "#333333"

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

C_BG = "#F5F3EF"
C_BG_ALT = "#EDEAE4"
C_CARD = "#FFFFFF"
C_BORDER = "#D5D2CB"
C_BORDER_STRONG = "#B5B2AB"

# --- Palette moderne (overhaul visuel session 2026-09-09) ---------------
# Sidebar « encre + ambre » : fond sombre profond, accents or de la marque.
C_INK = "#1C2233"
C_INK_2 = "#27304A"
C_SIDEBAR_TEXT = "#EDF0F7"
C_SIDEBAR_MUTED = "#9AA3BD"
C_SIDEBAR_HOVER = "rgba(255, 255, 255, 0.07)"
C_SIDEBAR_ACTIVE = "rgba(244, 186, 63, 0.16)"
C_BG_SOFT = "#F8F6F2"
C_SHADOW = "50, 20, 20"
C_FOCUS_RING = "#E8A63C"
C_GRAD_TOP = "#EAB43B"
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

STYLE_BTN_PRIMARY = (
    f"background-color: {C_PRIMARY}; color: #000000; border: none;"
    f" border-radius: 11px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_SECONDARY = (
    f"background-color: {C_CARD}; color: {C_TEXT_SECONDARY}; border: 1px solid {C_BORDER_STRONG};"
    f" border-radius: 11px; padding: 10px 22px; font-weight: 600; font-size: 13px;"
)
STYLE_BTN_SUCCESS = (
    f"background-color: {C_PRIMARY}; color: #000000; border: none;"
    f" border-radius: 11px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_DANGER = (
    f"background-color: {C_DANGER_BG}; color: {C_DANGER}; border: 1px solid {C_DANGER_BORDER};"
    f" border-radius: 11px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_ADD = (
    f"background-color: {C_PRIMARY_BG}; color: {C_PRIMARY}; border: 1px solid {C_GOLD_BORDER};"
    f" border-radius: 11px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_CARD = (
    f"background: {C_CARD}; border: 1px solid #E6E3DB;"
    f" border-radius: 14px; padding: 16px;"
    f" background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    f" stop:0 #FFFFFF, stop:1 #FAF9F6);"
)
STYLE_SELECTOR = (
    f"background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: 11px; padding: 8px 16px;"
)

STYLE_HEADER_TITLE = f"font-size: 22px; font-weight: 700; color: {C_TEXT}; margin: 0;"
STYLE_HEADER_SUBTITLE = f"font-size: 13px; color: {C_TEXT_MUTED}; margin: 0 0 4px 0;"
STYLE_EMPTY_STATE = f"color: {C_EMPTY_STATE}; font-size: 14px; padding: 40px;"
STYLE_STATUS = f"color: {C_TEXT_MUTED}; font-size: 12px; padding: 4px;"

STYLE_TABLE = (
    f"QTableWidget {{ background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: 12px; gridline-color: transparent; font-size: 13px;"
    f" alternate-background-color: #F7F5F0; }}"
    f"QTableWidget::item {{ padding: 6px 10px; border-bottom: 1px solid #EFECE6; }}"
    f"QTableWidget::item:selected {{ background: {C_PRIMARY_LIGHT}; color: {C_PRIMARY_PRESSED}; }}"
    f"QTableWidget::item:hover {{ background: {C_PRIMARY_BG}; }}"
    f"QHeaderView::section {{ background: #F3F1EC; color: {C_TEXT_MUTED};"
    f" font-weight: 700; font-size: 12px; padding: 11px 10px; border: none;"
    f" border-bottom: 2px solid {C_PRIMARY}; }}"
    f"QTableCornerButton::section {{ background: #F3F1EC; border: none; }}"
)


APP_STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    font-family: 'Inter', 'Segoe UI', 'Lato', 'DejaVu Sans', sans-serif;
    font-size: 11pt; color: {C_TEXT};
}}
QMainWindow {{ background-color: {C_BG}; }}

QToolTip {{
    background-color: {C_INK}; color: {C_SIDEBAR_TEXT};
    padding: 7px 12px; border-radius: 8px; font-size: 12px;
    border: 1px solid {C_INK_2};
}}

QPushButton {{
    background-color: {C_CARD}; color: {C_TEXT_SECONDARY};
    border: 1px solid {C_BORDER_STRONG}; border-radius: 10px;
    padding: 9px 20px; font-weight: 600; font-size: 13px;
}}
QPushButton:hover {{ background-color: {C_PRIMARY_BG}; border-color: {C_PRIMARY}; }}
QPushButton:pressed {{ background-color: {C_PRIMARY_LIGHT}; }}
QPushButton:default {{ background-color: {C_PRIMARY}; color: #000000; border: none; font-weight: 700; }}
QPushButton:default:hover {{ background-color: {C_PRIMARY_HOVER}; }}
QPushButton:disabled {{ background-color: #EFECE6; color: {C_TEXT_MUTED}; border-color: #E6E3DB; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C9C4B9; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {C_PRIMARY}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C9C4B9; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {C_PRIMARY}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

{STYLE_TABLE}

QMenu {{
    background-color: {C_CARD}; border: 1px solid {C_BORDER};
    border-radius: 10px; padding: 6px;
}}
QMenu::item {{ padding: 8px 26px 8px 14px; border-radius: 7px; color: {C_TEXT_SECONDARY}; }}
QMenu::item:selected {{ background-color: {C_PRIMARY}; color: #000000; font-weight: 700; }}

QStatusBar {{
    background: {C_CARD}; color: {C_TEXT_MUTED};
    border-top: 1px solid #EBE8E1; font-size: 12px;
}}
QMessageBox QPushButton, QDialog QPushButton {{
    min-height: 36px; padding: 8px 22px; border-radius: 10px;
}}

QListWidget {{
    background: transparent; border: none;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: 9px; color: {C_TEXT_SECONDARY}; }}
QListWidget::item:hover {{ background-color: {C_PRIMARY_BG}; }}
QListWidget::item:selected {{ background-color: {C_PRIMARY_LIGHT}; color: {C_PRIMARY}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    border: 1px solid {C_BORDER_STRONG}; border-radius: 10px; padding: 8px 12px;
    background-color: {C_CARD}; color: {C_TEXT}; font-size: 13px;
    selection-background-color: {C_PRIMARY_LIGHT};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
    border: 1px solid {C_TEXT_MUTED};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {C_FOCUS_RING};
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
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 10px;
    selection-background-color: {C_PRIMARY}; selection-color: #000000;
    padding: 4px; color: {C_TEXT_SECONDARY};
}}

QCheckBox {{ spacing: 8px; color: {C_TEXT_SECONDARY}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border: 2px solid {C_BORDER_STRONG};
    border-radius: 6px; background: {C_CARD};
}}
QCheckBox::indicator:hover {{ border-color: {C_PRIMARY}; }}
QCheckBox::indicator:checked {{
    background-color: {C_PRIMARY}; border-color: {C_PRIMARY_PRESSED};
}}

QGroupBox {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 14px;
    margin-top: 12px; padding: 14px 12px 12px 12px; font-weight: 700;
    font-size: 13px; color: {C_TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 14px; top: 2px; padding: 0 8px;
    background: {C_BG}; color: {C_TEXT_MUTED};
}}

QTabWidget::pane {{ border: none; background: transparent; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {C_TEXT_MUTED}; padding: 10px 22px;
    margin-right: 4px; border: none; font-weight: 600; font-size: 13px;
    border-radius: 10px; margin-top: 6px;
}}
QTabBar::tab:hover {{ background: {C_PRIMARY_BG}; color: {C_PRIMARY}; }}
QTabBar::tab:selected {{
    background: {C_PRIMARY_LIGHT}; color: {C_PRIMARY}; font-weight: 700;
}}

QLabel {{ color: {C_TEXT_SECONDARY}; }}

QCalendarWidget QWidget {{ alternate-background-color: {C_PRIMARY_BG}; }}
"""


QSS_SIDEBAR = f"""
QPushButton {{
    color: {C_SIDEBAR_TEXT};
    border-radius: 10px; font-size: 13px; font-weight: 500; background: transparent;
    text-align: left; padding: 10px 16px; border: none;
}}
QPushButton:hover {{
    background-color: {C_SIDEBAR_HOVER};
}}
QPushButton:checked {{
    background-color: {C_SIDEBAR_ACTIVE};
    border-left: 3px solid {C_PRIMARY};
    color: #F6C866; font-weight: 700;
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


def lire_config_sync() -> dict:
    import json
    try:
        return json.loads(fichier_config_sync().read_text(encoding="utf-8"))
    except Exception:
        return {}


def ecrire_config_sync(**valeurs) -> None:
    import json
    cfg = lire_config_sync()
    cfg.update(valeurs)
    fichier_config_sync().write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


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
