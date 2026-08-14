import os
import sys
from pathlib import Path

# nom et version de l'app
APP_NAME = "Gestion Scolaire"
APP_VERSION = "1.2.0"

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

# police utilisee dans toute l'interface, avec une liste de secours
APP_FONT_FAMILY = "Segoe UI"
APP_FONT_FALLBACK = ("DejaVu Sans", "Noto Sans", "Ubuntu", "Helvetica", "sans-serif")
APP_FONT_SIZE = 10

# serveur optionnel ; l'app fonctionne aussi sans lui, en local
API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 3.0

# infos locales par defaut de l'ecole
PAYS_DEFAUT = "Republique du Congo"
VILLE_DEFAUT = "Brazzaville"
INDICATIF_TEL = "+242"
DEVISE = "FCFA"

# feuille de style qui habille toutes les fenetres
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

# roles autorises pour les comptes, et leur libelle dans l'interface
ROLES = ("admin", "directeur", "gestionnaire")

ROLE_LABELS = {
    "admin": "Administrateur",
    "directeur": "Directeur",
    "gestionnaire": "Gestionnaire",
}

# listes fixees : periodes de l'annee, jours d'ecole et creneaux de cours
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

# retrouve le chemin d'un fichier, meme quand l'app est un executable
def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).parent / relative

# dossier des donnees de l'app, cree automatiquement si besoin
def data_dir() -> Path:
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

# comptes crees automatiquement au premier lancement
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

# matieres ajoutees automatiquement au premier lancement
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
