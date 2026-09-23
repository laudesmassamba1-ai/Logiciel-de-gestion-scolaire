"""KPICard — carte de chiffre cle, UNE seule implementation pour toute l'appli.

Carte « Apple minimal » : fond blanc, coins uniformes, hairline 1 px, aucune
ombre ni bande. Le fond est un SPRITE pre-rendu par `resources.cel_engine`
(net au pixel pres a toute densite d'ecran) assigne a la taille logique du
widget puis cache par rayon/dpr. Aucun style applique par feuille de style ;
le sprite est AFFICHE tel quel.

Hauteur FIXE, jamais expanding :
- label (caption, TEXT_MUTED) en haut
- valeur (title, TEXT_PRIMARY ou couleur semantique) en dessous
- espaces serres entre les deux
"""

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QLabel, QVBoxLayout

from qfluentwidgets import CardWidget

from resources.design_tokens import Colors, FontFamily, FontSize, Radius, Spacing
from resources.cel_engine import carte_pour, dpr_reel, sprite_carte
from core.config import T_KPI_HAUTEUR


class KPICard(CardWidget):
    """Hauteur FIXE (112 px), jamais expanding. Ombre portee NETTE
    (blur 0 = effet « sticker » cartoon, volontairement pro)."""

    def __init__(self, label, valeur="0", couleur=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(T_KPI_HAUTEUR)
        self.setMinimumWidth(170)
        self.setBorderRadius(Radius.LG)
        self.setObjectName("kpiCard")

        self._sprite = None  # cree dans resizeEvent

        # Ombre dure cartoon : nette (blur 0), decalee de 4 px vers le bas.
        ombre = QGraphicsDropShadowEffect(self)
        ombre.setBlurRadius(0)
        ombre.setOffset(0, 4)
        ombre.setColor(QColor(36, 52, 100, 42))  # rgba 16 %
        self.setGraphicsEffect(ombre)

        self._label = QLabel(label)
        self._label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {FontSize.CAPTION - 1}px;"
            " font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px;"
            " border: none; background: transparent;")
        self._valeur = QLabel(str(valeur))
        self._valeur.setStyleSheet(self._style_valeur(couleur))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        lay.setSpacing(Spacing.XS)
        lay.addWidget(self._label)
        lay.addWidget(self._valeur)
        lay.addStretch(1)

    def _style_valeur(self, couleur):
        base = (f"font-family: '{FontFamily.DISPLAY}', '{FontFamily.BODY}', '{FontFamily.EMOJI}', 'Segoe UI', sans-serif;"
                f" font-size: {FontSize.DISPLAY}px; font-weight: 800;"
                " letter-spacing: -0.5px;"
                " border: none; background: transparent;")
        return f"{base} color: {couleur or Colors.TEXT_PRIMARY};"

    def set_value(self, nouvelle_valeur):
        """Mise a jour sans recreer le widget."""
        self._valeur.setText(str(nouvelle_valeur))

    def resizeEvent(self, event):
        """(Re)genere le sprite a la taille exacte du widget, une fois par
        resize (la hauteur est fixe, la largeur varie avec le grid)."""
        super().resizeEvent(event)
        self._sprite, self._dpr = carte_pour(self, rayon=Radius.LG)
        self.update()

    def paintEvent(self, event):
        """Affiche le sprite de la carte (coins uniformes + hairline 1 px),
        rendu a la resolution reelle (HiDPI)."""
        if self._sprite is not None:
            p = QPainter(self)
            p.drawPixmap(0, 0, self._sprite)
            p.end()
        else:
            super().paintEvent(event)
