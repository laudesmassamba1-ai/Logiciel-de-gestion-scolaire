"""PageHeader — titre + sous-titre + zone d'actions, meme agencement partout."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from resources.design_tokens import Colors, FontSize, Spacing


class PageHeader(QFrame):
    def __init__(self, titre, sous_titre="", parent=None):
        super().__init__(parent)
        self.setObjectName("entete_page")
        self.setStyleSheet("QFrame#entete_page { border: none; background: transparent; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.LG)

        colonne = QVBoxLayout()
        colonne.setSpacing(Spacing.XS)
        lbl_titre = QLabel(titre)
        lbl_titre.setStyleSheet(
            f"font-size: {FontSize.PAGE_TITLE}px; font-weight: 700;"
            f" color: {Colors.TEXT_PRIMARY}; border: none; background: transparent;")
        self._accroche = None
        accroche = QLabel(sous_titre) if sous_titre else QLabel()
        if sous_titre:
            accroche.setStyleSheet(
                f"font-size: {FontSize.BODY}px; color: {Colors.TEXT_MUTED};"
                " border: none; background: transparent;")
        self._accroche = accroche
        colonne.addWidget(lbl_titre)
        if sous_titre:
            colonne.addWidget(accroche)

        accent = QFrame()
        accent.setFixedSize(46, 3)
        accent.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {Colors.PRIMARY}, stop:1 rgba(218,165,32,0));"
            " border: none; border-radius: 2px; margin-top: 2px;")
        colonne.addWidget(accent)

        lay.addLayout(colonne)
        lay.addStretch(1)

        self.actions_zone = QHBoxLayout()
        self.actions_zone.setSpacing(Spacing.SM)
        lay.addLayout(self.actions_zone)

    def ajouter_action(self, widget):
        self.actions_zone.addWidget(widget)

    def set_sous_titre(self, texte):
        if self._accroche is not None:
            self._accroche.setText(texte)
            self._accroche.setVisible(bool(texte))