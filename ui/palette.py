"""Palette de commandes « Spotlight » : Ctrl+K pour chercher et atteindre
instantanement une section ou lancer une action.

Affichee en haut centre de la fenetre : champ de recherche, liste filtree
en direct (sans accent, insensible a la casse), fleches haut/bas pour
parcourir, Entree pour valider, Echap pour fermer.

Signal :
    Palette.choisi(cle)   -> la cle d'une entree selectionnee.
    Palette.annule()      -> fermeture sans choix.
"""

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QVBoxLayout,
)

from core.config import (
    C_INK, C_PRIMARY_LIGHT, C_PRIMARY_BG, C_TEXT_MUTED, C_BORDER,
)

_SEPARATEUR = "#1F2A44"
_GOLD = "#C8960C"


def _normaliser(texte):
    """Minuscules sans accents pour une correspondance tolerante."""
    repl = str.maketrans({
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "œ": "oe", "æ": "ae",
    })
    return texte.lower().translate(repl)


class _Saisie(QLineEdit):
    def __init__(self, palette):
        super().__init__()
        self._palette = palette

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self._palette._suivant(1)
            return
        if event.key() == Qt.Key_Up:
            self._palette._suivant(-1)
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._palette._activer()
            return
        if event.key() == Qt.Key_Escape:
            self._palette._fermer()
            return
        super().keyPressEvent(event)


class Palette(QFrame):
    choisi = pyqtSignal(str)
    annule = pyqtSignal()

    def __init__(self, parent):
        super().__init__(None)
        self._parent = parent
        self._entrees = []
        self._bloque = False

        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(540)

        ombre = QGraphicsDropShadowEffect(self)
        ombre.setBlurRadius(40)
        ombre.setOffset(0, 12)
        ombre.setColor(QColor(15, 18, 28, 120))
        self.setGraphicsEffect(ombre)

        carte = QFrame()
        carte.setObjectName("paletteCarte")
        carte.setStyleSheet(
            f"QFrame#paletteCarte {{ background-color: #FFFFFF;"
            f" border: 2px solid #C7CFDD; border-radius: 16px; }}")

        v = QVBoxLayout(carte)
        v.setContentsMargins(6, 6, 6, 10)
        v.setSpacing(4)

        ligne = QHBoxLayout()
        ligne.setContentsMargins(14, 6, 14, 6)
        glow = QLabel("palette")
        glow.setFixedSize(10, 10)
        glow.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f" stop:0 #EAB43B, stop:1 #C28C0C); border: none;"
            f" border-radius: 5px;")
        self.saisie = _Saisie(self)
        self.saisie.setPlaceholderText("Rechercher une section ou une action…")
        self.saisie.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none;"
            f" color: {C_INK}; font-size: 15px; font-weight: 600;"
            f" padding: 8px; }}"
            f"QLineEdit:focus {{ border: none; }}")
        raccourci = QLabel("Ctrl+K")
        raccourci.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 11px; font-weight: 700;"
            f" background: #EEF2F8; border: 1px solid #DDE3ED;"
            f" border-radius: 12px; padding: 3px 8px;")
        ligne.addWidget(glow)
        ligne.addWidget(self.saisie, 1)
        ligne.addWidget(raccourci)
        v.addLayout(ligne)

        trait = QFrame()
        trait.setFixedHeight(1)
        trait.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 #00000000, stop:0.5 {_GOLD}, stop:1 #00000000);")
        v.addWidget(trait)

        self.liste = QListWidget()
        self.liste.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none;"
            f" font-size: 14px; font-weight: 600; color: {C_INK}; }}"
            f"QListWidget::item {{ padding: 10px 16px; border-radius: 12px;"
            f" margin: 2px 4px; }}"
            f"QListWidget::item:selected {{ background: {C_PRIMARY_BG};"
            f" color: #7A5A00; border: 3px solid {_GOLD};"
            f" padding-left: 13px; }}")
        self.liste.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(self.liste)

        zone = QVBoxLayout(self)
        zone.setContentsMargins(0, 0, 0, 0)
        zone.addWidget(carte)

        self.saisie.textChanged.connect(self._filtrer)
        self.saisie.returnPressed.connect(self._activer)
        self.liste.itemActivated.connect(lambda _it: self._activer())
        self.liste.itemClicked.connect(lambda _it: self._activer())

        self.setMinimumSize(540, 0)

    def maj_entrees(self, entrees):
        """entrees : liste de (titre, conseil, cle)."""
        self._entrees = entrees
        self._filtrer(self.saisie.text())

    def ouvrir(self, entrees=None, filtre=""):
        self._bloque = False
        if entrees is not None:
            self.maj_entrees(entrees)
        self._positionner()
        self.show()
        self.raise_()
        self.setFocus()
        self.saisie.clear()
        if filtre:
            self.saisie.setText(filtre)
        self.saisie.setFocus()

    def _positionner(self):
        pos = self._parent.mapToGlobal(QPoint(0, 0))
        x = int(pos.x() + (self._parent.width() - self.width()) / 2)
        y = int(pos.y() + 60)
        self.move(x, y)

    def _filtrer(self, texte):
        cible = _normaliser(texte)
        self.liste.clear()
        for titre, conseil, cle in self._entrees:
            if cible in _normaliser(titre) or cible in _normaliser(conseil):
                item = QListWidgetItem(f"{titre}   ·   {conseil}" if conseil
                                       else titre)
                item.setData(Qt.UserRole, (cle, titre))
                self.liste.addItem(item)
        if self.liste.count():
            self.liste.setCurrentRow(0)
            self.liste.setFixedHeight(
                min(22 + self.liste.sizeHintForRow(0) * self.liste.count(),
                    420))
        else:
            self.liste.setFixedHeight(0)

    def _suivant(self, sens):
        n = self.liste.count()
        if not n:
            return
        self.liste.setCurrentRow((self.liste.currentRow() + sens) % n)

    def _activer(self):
        if self._bloque:
            return
        item = self.liste.currentItem()
        if item is None:
            return
        cle, _titre = item.data(Qt.UserRole)
        self._bloque = True
        self._fermer()
        self.choisi.emit(cle)

    def _fermer(self):
        if self.isVisible():
            self.hide()
            self.annule.emit()