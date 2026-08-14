
from PyQt5.QtWidgets import QSizePolicy, QTableView
from PyQt5.uic import loadUi

from core.config import UI_DIR


def _make_responsive(widget):
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    for table in widget.findChildren(QTableView):
        try:
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except (AttributeError, TypeError):
            pass
    return widget


def load_ui(relative_path: str, widget=None):
    path = UI_DIR / relative_path
    result = loadUi(str(path), widget)
    return _make_responsive(result if result else widget)


def apply_ui(relative_path: str, widget):
    loadUi(str(UI_DIR / relative_path), widget)
    return _make_responsive(widget)
