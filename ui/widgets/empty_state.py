"""EmptyState — etat vide compact et centralise (jamais plus d'un endroit)."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QLabel, QPushButton, QVBoxLayout,
)

from resources.design_tokens import Colors, FontSize, Radius, Spacing

try:
    import qtawesome as _qta
except Exception:  # pragma: no cover - qtawesome optionnel
    _qta = None


class EmptyState(QFrame):
    """Message centre (+ icone + bouton d'action optionnel).

    Hauteur MINIMALE (200 px par defaut) et jamais etirable : un etat vide
    ne doit jamais creer un grand vide visuel sous le contenu, mais il peut
    grandir si le contenu (texte long sur plusieurs lignes) l'exige.
    """

    def __init__(self, texte, sous_titre="", bouton=None, icone="fa5s.inbox",
                 hauteur=200, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(hauteur)
        # Ombre portee presque nette : détache l'etat vide du fond aurora.
        ombre = QGraphicsDropShadowEffect(self)
        ombre.setBlurRadius(3)
        ombre.setOffset(0, 3)
        ombre.setColor(QColor(31, 45, 80, 26))  # ~10 %
        self.setGraphicsEffect(ombre)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        lay.setSpacing(Spacing.MD)
        lay.setAlignment(Qt.AlignCenter)

        if _qta is not None:
            ic = _qta.icon(icone, color=Colors.TEXT_LIGHT)
            lbl_ic = QLabel()
            lbl_ic.setPixmap(ic.pixmap(48, 48))
            lbl_ic.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl_ic)
            lay.addSpacing(Spacing.XS)

        self._lbl_msg = QLabel(texte)
        self._lbl_msg.setStyleSheet(
            f"color: {Colors.EMPTY_STATE}; font-size: {FontSize.TITLE}px;"
            " font-weight: 700; background: transparent; border: none;")
        self._lbl_msg.setAlignment(Qt.AlignCenter)
        self._lbl_msg.setWordWrap(True)
        lay.addWidget(self._lbl_msg)

        self._lbl_sous = QLabel(sous_titre)
        self._lbl_sous.setStyleSheet(
            f"color: {Colors.TEXT_LIGHT}; font-size: {FontSize.BODY}px;"
            " background: transparent; border: none;")
        self._lbl_sous.setAlignment(Qt.AlignCenter)
        self._lbl_sous.setVisible(bool(sous_titre))
        lay.addWidget(self._lbl_sous)

        if bouton is not None:
            lay.addSpacing(Spacing.SM)
            lay.addWidget(bouton, 0, Qt.AlignHCenter)

        self.bouton = bouton
        self.setStyleSheet(
            f"QFrame {{ background: {Colors.BG_CARD};"
            f" border: 1px dashed {Colors.BORDER_STRONG};"
            f" border-radius: {Radius.LG}px; }}")

    def set_message(self, texte, sous_titre=""):
        self._lbl_msg.setText(texte)
        self._lbl_sous.setText(sous_titre)
        self._lbl_sous.setVisible(bool(sous_titre))