import os
import sys
from pathlib import Path


APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.3.0"

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"


APP_FONT_FAMILY = "Inter"
APP_FONT_FALLBACK = ("Segoe UI", "Calibri", "Lato", "DejaVu Sans", "Noto Sans", "Arial", "sans-serif")
APP_FONT_SIZE = 11


API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 2.0


PAYS_DEFAUT = "Republique du Congo"
VILLE_DEFAUT = "Brazzaville"
INDICATIF_TEL = "+242"
DEVISE = "FCFA"


C_TEXT = "#1e293b"
C_TEXT_SECONDARY = "#334155"
C_TEXT_MUTED = "#475569"
C_TEXT_LIGHT = "#64748b"
C_EMPTY_STATE = "#64748b"

C_PRIMARY = "#047857"
C_PRIMARY_HOVER = "#059669"
C_PRIMARY_PRESSED = "#065f46"
C_PRIMARY_LIGHT = "#d1fae5"
C_PRIMARY_BG = "#ecfdf5"

C_BG = "#f8fafc"
C_BG_ALT = "#f1f5f9"
C_CARD = "#ffffff"
C_BORDER = "#e2e8f0"
C_BORDER_STRONG = "#d1d5db"

C_SUCCESS = "#10b981"
C_SUCCESS_DARK = "#059669"
C_DANGER = "#dc2626"
C_DANGER_BG = "#fef2f2"
C_DANGER_BORDER = "#fecaca"
C_WARNING = "#d97706"
C_INFO = "#2563eb"

STYLE_BTN_PRIMARY = (
    f"background-color: {C_PRIMARY}; color: white; border: none;"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_SECONDARY = (
    f"background-color: {C_CARD}; color: {C_TEXT_SECONDARY}; border: 1px solid {C_BORDER_STRONG};"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 600; font-size: 13px;"
)
STYLE_BTN_SUCCESS = (
    f"background-color: {C_SUCCESS}; color: white; border: none;"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_DANGER = (
    f"background-color: {C_DANGER_BG}; color: {C_DANGER}; border: 1px solid {C_DANGER_BORDER};"
    f" border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;"
)
STYLE_BTN_ADD = (
    f"background-color: {C_PRIMARY_BG}; color: {C_PRIMARY}; border: 1px solid #a7f3d0;"
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
    f" border-radius: 10px; gridline-color: #f1f5f9; font-size: 13px; }}"
    f"QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #f1f5f9; }}"
    f"QTableWidget::item:selected {{ background: {C_PRIMARY_LIGHT}; color: #064e3b; }}"
    f"QTableWidget::item:hover {{ background: #f0fdf4; }}"
    f"QHeaderView::section {{ background: #f8fafc; color: {C_TEXT_MUTED};"
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
    background-color: #0f172a; color: #ffffff; border: none;
    padding: 6px 10px; border-radius: 6px; font-size: 12px;
}}

QPushButton {{
    background-color: {C_PRIMARY}; color: white; border: none;
    border-radius: 8px; padding: 10px 22px; font-weight: 700; font-size: 13px;
}}
QPushButton:hover {{ background-color: {C_PRIMARY_HOVER}; }}
QPushButton:pressed {{ background-color: {C_PRIMARY_PRESSED}; }}
QPushButton:disabled {{ background-color: #cbd5e1; color: #f8fafc; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #cbd5e1; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: #94a3b8; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #cbd5e1; border-radius: 4px; min-width: 32px; }}
QScrollBar::handle:horizontal:hover {{ background: #94a3b8; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

{STYLE_TABLE}

QMenu {{
    background-color: {C_CARD}; border: 1px solid {C_BORDER};
    border-radius: 8px; padding: 6px;
}}
QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 6px; color: {C_TEXT_SECONDARY}; }}
QMenu::item:selected {{ background-color: {C_PRIMARY_LIGHT}; color: #064e3b; }}

QStatusBar {{
    background: {C_CARD}; color: {C_TEXT_MUTED};
    border-top: 1px solid {C_BORDER}; font-size: 12px;
}}
QMessageBox QPushButton, QDialog QPushButton {{
    min-height: 36px; padding: 8px 22px; border-radius: 8px;
}}

QListWidget::item {{ padding: 8px 6px; border-radius: 6px; color: {C_TEXT_SECONDARY}; }}
QListWidget::item:selected {{ background-color: {C_PRIMARY_LIGHT}; color: #064e3b; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {{
    border: 1px solid {C_BORDER_STRONG}; border-radius: 8px; padding: 8px 12px;
    background-color: {C_CARD}; color: {C_TEXT}; font-size: 13px;
    selection-background-color: {C_PRIMARY_LIGHT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 2px solid {C_SUCCESS}; background-color: {C_CARD};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    image: none; border-left: 5px solid transparent;
    border-right: 5px solid transparent; border-top: 6px solid {C_TEXT_MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
    selection-background-color: {C_PRIMARY_LIGHT}; selection-color: #064e3b;
    padding: 4px; color: {C_TEXT_SECONDARY};
}}

QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: {C_BG_ALT}; color: {C_TEXT_MUTED}; padding: 10px 22px;
    margin-right: 2px; border: none; font-weight: 600; font-size: 13px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:hover {{ background: #e2e8f0; color: {C_TEXT_SECONDARY}; }}
QTabBar::tab:selected {{
    background: {C_CARD}; color: {C_PRIMARY}; font-weight: 700;
    border-bottom: 2px solid {C_SUCCESS};
}}

QLabel {{ color: {C_TEXT_SECONDARY}; }}
"""


QSS_SIDEBAR = f"""
#sidebar {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #047857, stop:1 #065f46); border: none; }}
#lbl_logo {{ color: #ffffff; font-size: 17px; font-weight: 700; padding: 8px 20px 16px 20px; letter-spacing: 0.5px; }}
#sidebar QPushButton {{
    color: #d1fae5; text-align: left; padding: 12px 22px; border: none; margin: 1px 12px;
    border-radius: 10px; font-size: 13px; font-weight: 500; background: transparent;
}}
#sidebar QPushButton:hover {{ background-color: rgba(255,255,255,0.10); color: #ffffff; }}
#sidebar QPushButton:pressed {{ background-color: rgba(255,255,255,0.18); }}
#sidebar QPushButton:checked {{
    background-color: #ffffff; color: #047857; font-weight: 700;
    border-left: 3px solid #34d399;
}}
#userBox {{ background-color: rgba(255,255,255,0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 12px; margin: 8px 12px; }}
#lbl_user_name {{ color: #ffffff; font-size: 13px; font-weight: 700; }}
#lbl_user_role {{ color: #6ee7b7; font-size: 11px; font-weight: 600; }}
#btn_logout {{ color: #fca5a5; text-align: left; border: none; font-size: 12px; padding: 6px 0px; background: transparent; border-radius: 8px; }}
#btn_logout:hover {{ color: #ffffff; background-color: rgba(255,255,255,0.10); }}
"""


ROLES = ("admin", "directeur", "gestionnaire")

ROLE_LABELS = {
    "admin": "Administrateur",
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


DEFAULT_ACCOUNTS = (
    {"nom_complet": "Administrateur Systeme", "username": "admin",
     "email": "admin@ecole.cg", "telephone": "+242 06 000 0000",
     "password": "admin123", "role": "admin"},
    {"nom_complet": "Directeur de l'Ecole", "username": "directeur",
     "email": "directeur@ecole.cg", "telephone": "+242 06 000 0001",
     "password": "directeur123", "role": "directeur"},
    {"nom_complet": "Gestionnaire Scolaire", "username": "gestionnaire",
     "email": "gestionnaire@ecole.cg", "telephone": "+242 06 000 0002",
     "password": "gestionnaire123", "role": "gestionnaire"},
)


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
