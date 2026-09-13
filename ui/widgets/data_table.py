"""DataTable — tableau centralise, hauteur calculee sur le contenu.

Herite du `TableWidget` de PyQt-Fluent-Widgets. Une seule règle : la
hauteur est TOUJOURS recalculee a chaque changement de donnees via
`refresh_height()`, jamais fixee en dur ni laissee en `Expanding`. Aucune
table ne peut donc retrouver un vide sous ses lignes.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView, QTableWidgetItem

from qfluentwidgets import TableWidget

from resources.design_tokens import Colors, FontSize


class DataTable(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBorderVisible(False)
        self.setWordWrap(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(TableWidget.SelectRows)
        self.setSelectionMode(TableWidget.SingleSelection)
        self.setEditTriggers(TableWidget.NoEditTriggers)
        self.verticalHeader().setDefaultSectionSize(40)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(
            Qt.AlignLeft | Qt.AlignVCenter)
        self.horizontalHeader().setHighlightSections(False)
        self.setStyleSheet(self._qss())
        self.refresh_height()

    @staticmethod
    def _qss():
        return (
            "QTableWidget { background-color: #FFFFFF; alternate-background-color: #F6F8FB;"
            " border: 1px solid #DAE0EA; border-radius: 14px;"
            " gridline-color: #E7EBF3; padding: 2px; }"
            "QHeaderView::section { background-color: #F1F3F6; color: #3A3A40;"
            " font-weight: 700; font-size: 12px; border: none;"
            " border-bottom: 2px solid #C8960C; padding: 8px; }"
            "QTableWidget::item { padding: 6px 8px; }"
            "QTableWidget::item:selected { background-color: #FEF3C7; color: #1D1D1F; }"
            f"QTableWidget::item:hover {{ background-color: {Colors.PRIMARY_LIGHT}; }}"
            "QScrollBar:vertical { width: 10px; background: #F1F3F6;"
            " border-radius: 5px; margin: 2px; }"
            "QScrollBar::handle:vertical { background: #C4CCDA; border-radius: 5px; }"
        )

    def refresh_height(self, max_visible_rows=10):
        """Re-calcule la hauteur sur le contenu reel (ET une fois max)."""
        self.resizeRowsToContents()
        h = self.horizontalHeader().height() + 8
        comte = min(self.rowCount(), max(1, max_visible_rows))
        for i in range(comte):
            h += self.rowHeight(i)
        self.setMaximumHeight(h) if comte else self.setMaximumHeight(120)
        self.setMinimumHeight(min(h, 120))

    def remplir(self, valeurs, largeurs=None, stretch_index=None):
        """Remplit la table depuis une liste de ranges et re-themet la
        hauteur. `largeurs` : proportion en px par colonne si fournie."""
        if not valeurs:
            self.setRowCount(0)
            self.refresh_height()
            return self
        lignes = list(valeurs)
        colonnes = len(lignes[0])
        self.setColumnCount(colonnes)
        self.setRowCount(len(lignes))
        for i, ligne in enumerate(lignes):
            for j, val in enumerate(ligne):
                item = QTableWidgetItem("" if val is None else str(val))
                self.setItem(i, j, item)
        if largeurs:
            for j, w in enumerate(largeurs[:colonnes]):
                self.setColumnWidth(j, w)
        if stretch_index is not None:
            self.horizontalHeader().setSectionResizeMode(
                stretch_index, QHeaderView.Stretch)
        self.refresh_height()
        return self