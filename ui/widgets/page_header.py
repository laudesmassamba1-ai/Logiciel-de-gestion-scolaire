"""PageHeader — titre + zone d'actions, meme agencement partout."""

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from resources.design_tokens import Colors, FontFamily, FontSize, Spacing


class PageHeader(QFrame):
    def __init__(self, titre, parent=None):
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
            f"font-family: '{FontFamily.DISPLAY}', '{FontFamily.BODY}', '{FontFamily.EMOJI}', 'Segoe UI', sans-serif;"
            f" font-size: {FontSize.PAGE_TITLE}px; font-weight: 800;"
            " letter-spacing: -0.4px;"
            f" color: {Colors.TEXT_PRIMARY}; border: none; background: transparent;")
        colonne.addWidget(lbl_titre)

        accent = QFrame()
        accent.setFixedSize(46, 3)
        accent.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {Colors.GRAD_TOP}, stop:1 {Colors.GRAD_BOTTOM});"
            " border: none; border-radius: 2px; margin-top: 4px;")
        colonne.addWidget(accent)

        lay.addLayout(colonne)
        lay.addStretch(1)

        self.actions_zone = QHBoxLayout()
        self.actions_zone.setSpacing(Spacing.SM)
        lay.addLayout(self.actions_zone)

    def ajouter_action(self, widget):
        self.actions_zone.addWidget(widget)