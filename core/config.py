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
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_SECONDARY = (
    f"background-color: {C_CARD}; color: {C_TEXT_SECONDARY}; border: 1px solid {C_BORDER_STRONG};"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 600; font-size: 13px;"
)
STYLE_BTN_SUCCESS = (
    f"background-color: {C_PRIMARY}; color: #000000; border: none;"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_DANGER = (
    f"background-color: {C_DANGER_BG}; color: {C_DANGER}; border: 1px solid {C_DANGER_BORDER};"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_ADD = (
    f"background-color: {C_PRIMARY_BG}; color: {C_PRIMARY}; border: 1px solid {C_GOLD_BORDER};"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_CARD = (
    f"background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: 12px; padding: 16px;"
)
STYLE_SELECTOR = (
    f"background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: 10px; padding: 8px 16px;"
)

STYLE_HEADER_TITLE = f"font-size: 22px; font-weight: 700; color: {C_TEXT}; margin: 0;"
STYLE_HEADER_SUBTITLE = f"font-size: 13px; color: {C_TEXT_MUTED}; margin: 0 0 4px 0;"
STYLE_EMPTY_STATE = f"color: {C_EMPTY_STATE}; font-size: 14px; padding: 40px;"
STYLE_STATUS = f"color: {C_TEXT_MUTED}; font-size: 12px; padding: 4px;"

STYLE_TABLE = (
    f"QTableWidget {{ background: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: 10px; gridline-color: {C_BORDER}; font-size: 13px;"
    f" alternate-background-color: {C_BG_ALT}; }}"
    f"QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {C_BORDER}; }}"
    f"QTableWidget::item:selected {{ background: {C_PRIMARY_LIGHT}; color: {C_PRIMARY_PRESSED}; }}"
    f"QTableWidget::item:hover {{ background: {C_PRIMARY_BG}; }}"
    f"QHeaderView::section {{ background: {C_BG}; color: {C_TEXT_MUTED};"
    f" font-weight: 700; font-size: 12px; padding: 10px 8px; border: none;"
    f" border-bottom: 2px solid {C_BORDER}; }}"
)


APP_STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    font-family: 'Inter', 'Segoe UI', 'Lato', 'DejaVu Sans', sans-serif;
    font-size: 11pt; color: {C_TEXT};
}}
QMainWindow {{ background-color: {C_BG}; }}

QToolTip {{
    background-color: {C_CARD}; color: {C_TEXT_SECONDARY};
    padding: 6px 10px; border-radius: 6px; font-size: 12px;
    border: 1px solid {C_BORDER};
}}

QPushButton {{
    background-color: {C_PRIMARY}; color: #000000; border: none;
    border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;
}}
QPushButton:hover {{ background-color: {C_PRIMARY_HOVER}; }}
QPushButton:pressed {{ background-color: {C_PRIMARY_PRESSED}; }}
QPushButton:disabled {{ background-color: {C_BORDER}; color: {C_TEXT_MUTED}; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {C_BORDER_STRONG}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {C_TEXT_MUTED}; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {C_BORDER_STRONG}; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {C_TEXT_MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

{STYLE_TABLE}

QMenu {{
    background-color: {C_CARD}; border: 1px solid {C_BORDER};
    border-radius: 8px; padding: 6px;
}}
QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 6px; color: {C_TEXT_SECONDARY}; }}
QMenu::item:selected {{ background-color: {C_PRIMARY_LIGHT}; color: {C_PRIMARY}; }}

QStatusBar {{
    background: {C_CARD}; color: {C_TEXT_MUTED};
    border-top: 1px solid {C_BORDER}; font-size: 12px;
}}
QMessageBox QPushButton, QDialog QPushButton {{
    min-height: 36px; padding: 8px 22px; border-radius: 8px;
}}

QListWidget::item {{ padding: 8px 6px; border-radius: 6px; color: {C_TEXT_SECONDARY}; }}
QListWidget::item:selected {{ background-color: {C_PRIMARY_LIGHT}; color: {C_PRIMARY}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {{
    border: 1px solid {C_BORDER_STRONG}; border-radius: 8px; padding: 8px 12px;
    background-color: {C_CARD}; color: {C_TEXT}; font-size: 13px;
    selection-background-color: {C_PRIMARY_LIGHT};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
    border: 1px solid {C_TEXT_MUTED};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {C_SUCCESS}; background-color: {C_CARD};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QDateEdit:disabled, QTextEdit:disabled {{
    background-color: {C_BG_ALT}; color: {C_TEXT_MUTED}; border: 1px solid {C_BORDER};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    image: none; border-left: 5px solid transparent;
    border-right: 5px solid transparent; border-top: 6px solid {C_TEXT_MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
    selection-background-color: {C_PRIMARY_LIGHT}; selection-color: {C_PRIMARY};
    padding: 4px; color: {C_TEXT_SECONDARY};
}}

QCheckBox {{ spacing: 8px; color: {C_TEXT_SECONDARY}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border: 1px solid {C_BORDER_STRONG};
    border-radius: 5px; background: {C_CARD};
}}
QCheckBox::indicator:hover {{ border-color: {C_PRIMARY}; }}
QCheckBox::indicator:checked {{
    background-color: {C_PRIMARY}; border-color: {C_PRIMARY_PRESSED};
}}

QGroupBox {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 12px;
    margin-top: 12px; padding: 14px 12px 12px 12px; font-weight: 700;
    font-size: 13px; color: {C_TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 14px; top: 2px; padding: 0 6px;
    background: {C_BG}; color: {C_TEXT_MUTED};
}}

QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: {C_BG_ALT}; color: {C_TEXT_MUTED}; padding: 10px 22px;
    margin-right: 2px; border: none; font-weight: 600; font-size: 13px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:hover {{ background: {C_PRIMARY_BG}; }}
QTabBar::tab:selected {{
    background: {C_CARD}; color: {C_PRIMARY}; font-weight: 700;
    border-bottom: 2px solid {C_SUCCESS};
}}

QLabel {{ color: {C_TEXT_SECONDARY}; }}
"""


QSS_SIDEBAR = f"""
QPushButton {{
    color: {C_TEXT_SECONDARY};
    border-radius: 10px; font-size: 13px; font-weight: 500; background: transparent;
    text-align: left; padding: 10px 16px; border: none;
}}
QPushButton:hover {{
    background-color: {C_BG_ALT};
}}
QPushButton:checked {{
    background-color: {C_PRIMARY_LIGHT};
    border-left: 3px solid {C_PRIMARY};
    color: {C_PRIMARY};
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

os.makedirs(data_dir(), exist_ok=True)
