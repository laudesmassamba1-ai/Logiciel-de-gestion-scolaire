"""EmptyState — etat vide compact et centralise (jamais plus d'un endroit)."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from resources.design_tokens import Colors, FontSize, Radius, Spacing

try:
    import qtawesome as _qta
except Exception:  # pragma: no cover - qtawesome optionnel
    _qta = None


class EmptyState(QFrame):
    """Message centre (+ icone + bouton d'action optionnel).

    Hauteur fixe (~180 px), jamais etirable : un etat vide ne doit
    jamais creer un grand vide visuel sous le contenu.
    """

    def __init__(self, texte, sous_titre="", bouton=None, icone="fa5s.inbox",
                 hauteur=180, parent=None):
        super().__init__(parent)
        self.setFixedHeight(hauteur)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        lay.setSpacing(Spacing.SM)
        lay.setAlignment(Qt.AlignCenter)

        if _qta is not None:
            ic = _qta.icon(icone, color=Colors.TEXT_LIGHT)
            lbl_ic = QLabel()
            lbl_ic.setPixmap(ic.pixmap(36, 36))
            lbl_ic.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl_ic)

        self._lbl_msg = QLabel(texte)
        self._lbl_msg.setStyleSheet(
            f"color: {Colors.EMPTY_STATE}; font-size: {FontSize.SUBTITLE}px;"
            " font-weight: 600; background: transparent; border: none;")
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
            lay.addSpacing(Spacing.XS)
            lay.addWidget(bouton, 0, Qt.AlignHCenter)

        self.bouton = bouton
        self.setStyleSheet(
            f"QFrame {{ background: rgba(255,255,255,0.55);"
            f" border: 1px dashed {Colors.BORDER_STRONG};"
            f" border-radius: {Radius.LG}px; }}")

    def set_message(self, texte, sous_titre=""):
        self._lbl_msg.setText(texte)
        self._lbl_sous.setText(sous_titre)
        self._lbl_sous.setVisible(bool(sous_titre))