import os
import sys
from pathlib import Path


APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.2.0"

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")


APP_FONT_FAMILY = "Inter"
APP_FONT_FALLBACK = ("Segoe UI", "Lato", "DejaVu Sans", "Noto Sans", "sans-serif")
APP_FONT_SIZE = 10


API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 3.0


PAYS_DEFAUT = "Republique du Congo"
VILLE_DEFAUT = "Brazzaville"
INDICATIF_TEL = "+242"
DEVISE = "FCFA"


APP_STYLESHEET = """
QMainWindow, QDialog, QWidget { font-family: 'Inter', 'Segoe UI', 'Lato', 'DejaVu Sans', sans-serif; }
QToolTip { background-color: #0f172a; color: #ffffff; border: none; padding: 6px 8px; border-radius: 4px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #cbd5e1; border-radius: 5px; min-width: 28px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; gridline-color: #f1f5f9; }
QTableWidget::item { padding: 0px 6px; border: none; }
QTableWidget::item:selected { background-color: #d1fae5; color: #064e3b; }
QTableWidget::item:hover { background-color: #f0fdf4; }
QHeaderView::section { background: #f8fafc; color: #475569; font-weight: 600; padding: 10px 6px; border: none; border-bottom: 1px solid #e2e8f0; }

QMenu { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }
QMenu::item { padding: 8px 24px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background-color: #d1fae5; color: #064e3b; }
QStatusBar { background: #ffffff; color: #475569; border-top: 1px solid #e2e8f0; }
QMessageBox QPushButton, QDialog QPushButton { min-height: 32px; padding: 4px 18px; border-radius: 8px; }
QListWidget::item { padding: 8px 6px; border-radius: 6px; }
QListWidget::item:selected { background-color: #d1fae5; color: #064e3b; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
    border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px;
    background-color: #ffffff; color: #0f172a; selection-background-color: #d1fae5;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
    border: 1px solid #10b981; background-color: #ffffff;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #64748b; margin-right: 6px; }
QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; selection-background-color: #d1fae5; selection-color: #064e3b; }
QTabWidget::pane { border: none; background: transparent; top: -1px; }
QTabBar::tab { background: transparent; color: #64748b; padding: 10px 18px; margin-right: 4px; border: none; font-weight: 600; border-bottom: 2px solid transparent; }
QTabBar::tab:hover { color: #047857; }
QTabBar::tab:selected { color: #047857; border-bottom: 2px solid #10b981; }
QToolTip { background: #0f172a; color: #fff; }
"""


QSS_SIDEBAR = """
#sidebar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #047857, stop:1 #065f46); border: none; }
#lbl_logo { color: #ffffff; font-size: 17px; font-weight: 700; padding: 8px 20px 16px 20px; letter-spacing: 0.5px; }
#sidebar QPushButton {
    color: #d1fae5; text-align: left; padding: 12px 22px; border: none; margin: 1px 12px;
    border-radius: 10px; font-size: 13px; font-weight: 500; background: transparent;
}
#sidebar QPushButton:hover { background-color: rgba(255,255,255,0.10); color: #ffffff; }
#sidebar QPushButton:pressed { background-color: rgba(255,255,255,0.18); }
#sidebar QPushButton:checked {
    background-color: #ffffff; color: #047857; font-weight: 700;
    border-left: 3px solid #34d399;
}
#userBox { background-color: rgba(255,255,255,0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 12px; margin: 8px 12px; }
#lbl_user_name { color: #ffffff; font-size: 13px; font-weight: 700; }
#lbl_user_role { color: #a7f3d0; font-size: 11px; }
#btn_logout { color: #fca5a5; text-align: left; border: none; font-size: 12px; padding: 6px 0px; background: transparent; border-radius: 8px; }
#btn_logout:hover { color: #ffffff; background-color: rgba(255,255,255,0.10); }
"""

QSS_BOUTONS = """
QPushButton { border-radius: 8px; padding: 8px 16px; font-weight: 600; }
QPushButton { background-color: #047857; color: white; border: none; }
QPushButton:hover { background-color: #059669; }
QPushButton:pressed { background-color: #065f46; }
QPushButton:disabled { background-color: #cbd5e1; color: #f8fafc; }
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
    if hasattr(sys, "_MEIPASS"):
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
