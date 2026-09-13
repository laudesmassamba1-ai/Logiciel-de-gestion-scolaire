"""KPICard — carte de chiffre cle, une seule implementation pour toute l'appli.

Herite de `CardWidget` (PyQt-Fluent-Widgets) : bordure ronde, ombre douce.
Toute carte KPI de l'application doit passer par cette classe.
"""

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QLabel, QVBoxLayout

from qfluentwidgets import CardWidget

from resources.design_tokens import Colors, FontSize, Radius, Spacing


class KPICard(CardWidget):
    """Hauteur FIXE (88 px), jamais expanding.

    - label (caption, TEXT_SECONDARY) en haut
    - valeur (title, TEXT_PRIMARY ou couleur semantique) en dessous
    - espaces serres entre les deux
    """

    def __init__(self, label, valeur="0", couleur=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(88)
        self.setMinimumWidth(170)
        self.setBorderRadius(Radius.LG)
        self.setObjectName("kpiCard")

        self._label = QLabel(label)
        self._label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSize.CAPTION}px;"
            " font-weight: 600; border: none; background: transparent;")
        self._valeur = QLabel(str(valeur))
        self._valeur.setStyleSheet(self._style_valeur(couleur))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        lay.setSpacing(Spacing.XS)
        lay.addWidget(self._label)
        lay.addWidget(self._valeur)
        lay.addStretch(1)

        self.setStyleSheet(
            f"QFrame#kpiCard {{ background-color: {Colors.BG_CARD};"
            f" border: 3px solid {couleur or Colors.PRIMARY};"
            f" border-radius: {Radius.LG}px; }}")

    @staticmethod
    def _style_valeur(couleur):
        base = (f"font-size: {FontSize.TITLE}px; font-weight: 800;"
                " border: none; background: transparent;")
        return f"{base} color: {couleur or Colors.TEXT_PRIMARY};"

    def set_value(self, nouvelle_valeur):
        """Mise a jour sans recreer le widget."""
        self._valeur.setText(str(nouvelle_valeur))