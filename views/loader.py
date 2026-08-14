"""Gestion des fichiers UI : resolution du chemin (dev / PyInstaller) et chargement.

La fonction _make_responsive ne force PLUS chaque enfant en mode "Expanding"
ni ne remet les tailles minimales a 0 : c'etait la source des cartes ecrasees,
des textes tronques / chevauches et des graphiques invisibles. On laisse les
contraintes de hauteur/largeur definies dans les fichiers .ui s'appliquer, et
on ne rend expansible que la racine de chaque page.
"""
from PyQt5.QtWidgets import QSizePolicy, QTableView
from PyQt5.uic import loadUi

from config import UI_DIR


def _make_responsive(widget):
    """Rend la page racine expansible sans casser les tailles min/max du .ui."""
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    for table in widget.findChildren(QTableView):
        try:
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except (AttributeError, TypeError):
            pass
    return widget


def load_ui(relative_path: str, widget=None):
    """Charge un fichier .ui. Si un widget parent est fourni, y applique l'interface."""
    path = UI_DIR / relative_path
    result = loadUi(str(path), widget)
    return _make_responsive(result if result else widget)


def apply_ui(relative_path: str, widget):
    """Applique un fichier .ui a un widget existant (retourne le widget)."""
    loadUi(str(UI_DIR / relative_path), widget)
    return _make_responsive(widget)
