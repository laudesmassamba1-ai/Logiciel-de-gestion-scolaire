# petit utilitaire : charge les fichiers .ui et les rend extensibles
from PyQt5.QtWidgets import QSizePolicy, QTableView
from PyQt5.uic import loadUi

from core.config import UI_DIR

# rend le widget (et ses tableaux) extensibles pour occuper la fenetre
def _make_responsive(widget):
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    for table in widget.findChildren(QTableView):
        try:
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except (AttributeError, TypeError):
            pass
    return widget

# charge un fichier .ui depuis le dossier UI et le rend extensible
def load_ui(relative_path: str, widget=None):
    path = UI_DIR / relative_path
    result = loadUi(str(path), widget)
    return _make_responsive(result if result else widget)

# charge un fichier .ui directement dans le widget existant
def apply_ui(relative_path: str, widget):
    loadUi(str(UI_DIR / relative_path), widget)
    return _make_responsive(widget)
