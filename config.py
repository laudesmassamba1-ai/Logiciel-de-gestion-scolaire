"""Configuration globale de l'application.

Chemins, constantes et resolution des ressources qui fonctionne
aussi bien en developpement qu'avec un executable PyInstaller.
"""
import os
import sys
from pathlib import Path

APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.2.0"

# ---------------------------------------------------------------------------
# Rendu vectoriel net (anti-aliasing / High-DPI) sous Linux & Windows.
# A positionner AVANT l'instanciation de QApplication (voir main.py).
# ---------------------------------------------------------------------------
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

APP_FONT_FAMILY = "Segoe UI"
APP_FONT_FALLBACK = ("DejaVu Sans", "Noto Sans", "Ubuntu", "Helvetica", "sans-serif")
APP_FONT_SIZE = 10  # points : rendu lisible sans pixelisation

# ---------------------------------------------------------------------------
# API FastAPI (backend REST expose sur le port 8000)
# ---------------------------------------------------------------------------
API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 3.0  # secondes : pas d'attente bloquante si l'API est hors ligne

# Contexte national (Republique du Congo - Brazzaville)
PAYS_DEFAUT = "Republique du Congo"
VILLE_DEFAUT = "Brazzaville"
INDICATIF_TEL = "+242"
DEVISE = "FCFA"

# Feuille de style globale appliquee a toute l'application
APP_STYLESHEET = """
QMainWindow, QDialog, QWidget { font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; }
QToolTip { background-color: #0f172a; color: #ffffff; border: none; padding: 5px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QTableWidget::item { padding: 6px; }
QTableWidget::item:selected { background-color: #d1fae5; color: #064e3b; }
QTableWidget::item:hover { background-color: #f0fdf4; }
QMenu { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 4px; }
QMenu::item { padding: 8px 24px 8px 12px; border-radius: 4px; }
QMenu::item:selected { background-color: #d1fae5; color: #064e3b; }
QStatusBar { background: #ffffff; color: #475569; border-top: 1px solid #e2e8f0; }
QMessageBox QPushButton, QDialog QPushButton { min-height: 30px; padding: 4px 16px; }
QHeaderView::section { background-color: #f8fafc; color: #475569; font-weight: bold; padding: 6px; border: none; }
QListWidget::item { padding: 6px; }
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


def resource_path(relative: str) -> Path:
    """Resout un chemin vers les donnees empaquetees (zone _MEIPASS de PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).parent / relative


def data_dir() -> Path:
    """Dossier ou est stockee la base de donnees (ecriture autorisee)."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).parent
    folder = base / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


UI_DIR = resource_path("views/ui_files")
DB_PATH = data_dir() / "ecole.db"
DOCS_DIR = data_dir() / "documents"

# Comptes crees au premier lancement
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

# Matieres de base (notes + planning)
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
