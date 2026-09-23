"""DataTable — tableau centralise, hauteur calculee sur le contenu.

Herite du `TableWidget` de PyQt-Fluent-Widgets. Une seule règle : la
hauteur est TOUJOURS recalculee a chaque changement de donnees via
`refresh_height()`, jamais fixee en dur ni laissee en `Expanding`. Aucune
table ne peut donc retrouver un vide sous ses lignes.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QGraphicsDropShadowEffect, QHeaderView, QTableWidgetItem,
)

from qfluentwidgets import TableWidget

from resources.design_tokens import FontSize
from core.config import (
    C_BG_SOFT, C_BORDER_STRONG, C_CARD, C_CONTOUR, C_GRID, C_TEXT_SECONDARY,
    C_PRIMARY_LIGHT, C_SIDEBAR_ACTIVE_TEXT,
    T_RAYON_TABLE, T_TABLE_FONT, T_TABLE_PAD_Y, T_TABLE_PAD_X,
    T_TABLE_HEADER_FONT, T_TABLE_HEADER_PAD_Y, T_TABLE_HEADER_PAD_X,
)


class DataTable(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBorderVisible(False)
        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(TableWidget.SelectRows)
        self.setSelectionMode(TableWidget.SingleSelection)
        self.setEditTriggers(TableWidget.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(
            Qt.AlignLeft | Qt.AlignVCenter)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStyleSheet(
            f"QHeaderView {{ background: {C_BG_SOFT}; }}"
            "QHeaderView::section {"
            f" background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY};"
            f" font-weight: 700; font-size: {T_TABLE_HEADER_FONT}px;"
            " letter-spacing: 0.6px;"
            " text-transform: uppercase; border: none;"
            f" border-bottom: 2px solid {C_CONTOUR};"
            f" padding: {T_TABLE_HEADER_PAD_Y}px {T_TABLE_HEADER_PAD_X}px; }}"
        )
        self.setStyleSheet(self._qss())
        self.refresh_height()

        # Ombre portee NETTE (blur 0) : effet « sticker » cartoon mesuré.
        ombre = QGraphicsDropShadowEffect(self)
        ombre.setBlurRadius(0)
        ombre.setOffset(0, 4)
        ombre.setColor(QColor(31, 45, 80, 40))  # rgba ~16 %
        self.setGraphicsEffect(ombre)

    @staticmethod
    def _qss():
        return (
            "QTableWidget {"
            f" background-color: {C_CARD}; alternate-background-color: {C_BG_SOFT};"
            f" border: 1px solid {C_CONTOUR}; border-radius: {T_RAYON_TABLE}px;"
            f" gridline-color: {C_GRID}; padding: 2px; }}"
            "QHeaderView::section {"
            f" background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY};"
            f" font-weight: 700; font-size: {T_TABLE_HEADER_FONT}px;"
            " letter-spacing: 0.6px;"
            " text-transform: uppercase; border: none;"
            f" border-bottom: 2px solid {C_CONTOUR};"
            f" padding: {T_TABLE_HEADER_PAD_Y}px {T_TABLE_HEADER_PAD_X}px; }}"
            f"QTableWidget::item {{ padding: {T_TABLE_PAD_Y}px {T_TABLE_PAD_X}px;"
            f" border-bottom: 1px solid {C_GRID}; }}"
            "QTableWidget::item:selected {"
            f" background-color: {C_PRIMARY_LIGHT}; color: {C_SIDEBAR_ACTIVE_TEXT}; }}"
            "QTableWidget::item:hover {"
            f" background-color: {C_BG_SOFT}; }}"
            "QScrollBar:vertical { width: 10px; background: transparent;"
            " border-radius: 5px; margin: 2px; }"
            "QScrollBar::handle:vertical {"
            f" background: {C_BORDER_STRONG}; border-radius: 5px; }}"
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
        # Ne jamais REDUIRE le nombre de colonnes : certaines tables posent
        # leur header (4, 7, 9 colonnes...) puis remplissent moins de valeurs
        # par ligne ; setColumnCount plus petit detruirait les colonnes
        # restantes (ex. onglet "Programme par Classe" reduit a 1 colonne).
        colonnes = max(colonnes, self.columnCount())
        self.setColumnCount(colonnes)
        self.setRowCount(len(lignes))
        for i, ligne in enumerate(lignes):
            for j, val in enumerate(ligne):
                if j >= colonnes:
                    break
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