"""Notifications in-app style Apple : pilles arrondies qui glissent depuis
le haut droit de la fenetre, se fondent, s'empilent et disparaissent seules.

API publique :
    toast.afficher(parent, texte, type_="succes")
    toast.succes(parent, texte)
    toast.info(parent, texte)
    toast.erreur(parent, texte)

Design : carte blanche, ombre douce, pastille coloree a gauche, texte fonce.
Chaque notification : glissement horizontal + fondu (260 ms OutCubic),
pause, puis disparition (250 ms). Un clic la ferme immediatement.
Ancrees au coin superieur droit de la fenetre du widget parent ; jusqu'a
4 visibles (les plus anciennes remontent d'un cran avec animation).
"""

from PyQt5.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QWidget,
)

from core.config import (
    C_RED, C_RED_BG, C_GREEN, C_GREEN_BG, C_PRIMARY_PRESSED, C_PRIMARY_LIGHT,
    C_TEXT, C_BORDER,
)

_MARGE_X = 18
_MARGE_Y = 16
_ENTRE = 10
_MAX_VISIBLES = 4
_TAILLE_MIN = 300
_TAILLE_MAX = 400

_TYPES = {
    "succes": (C_GREEN, C_GREEN_BG),
    "info": (C_PRIMARY_PRESSED, C_PRIMARY_LIGHT),
    "erreur": (C_RED, C_RED_BG),
}

_VISIBLES = []


def succes(parent, texte):
    afficher(parent, texte, type_="succes")


def info(parent, texte):
    afficher(parent, texte, type_="info")


def erreur(parent, texte):
    afficher(parent, texte, type_="erreur")


def afficher(parent, texte, type_="succes", duree=None):
    durees = {"succes": 2600, "info": 3200, "erreur": 4600}
    duree = duree or durees.get(type_, 2600)
    try:
        ancre = parent.window() if isinstance(parent, QWidget) else parent
        if ancre is None or not ancre.isVisible():
            ancre = QApplication.activeWindow()
        if ancre is None:
            return
        _tronquer()
        toast = _Toast(ancre, texte, type_)
        _VISIBLES.append(toast)
        _repositionner(ancre, anime=True)
        toast._demarrer(duree)
    except RuntimeError:
        pass


def _repositionner(ancre, anime=False):
    """Empile les notifications en haut a droite de la fenetre.

    La plus recente est placee instantanement a sa position finale (son
    glissement d'arrivee est pilote par _Toast._demarrer) ; les autres
    remontent d'un cran, avec animation si `anime` est vrai.
    """
    if not _VISIBLES:
        return
    base = ancre.mapToGlobal(QPoint(0, 0))
    droite_x = base.x() + ancre.width() - _MARGE_X
    y = base.y() + _MARGE_Y
    derniere = _VISIBLES[-1]
    for t in _VISIBLES:
        cible = QPoint(int(droite_x - t.width()), int(y))
        t._cible_x = cible.x()
        if t is derniere:
            t.move(cible)
        elif anime:
            t._glisser_vers(cible.x(), 180)
        else:
            t.move(cible)
        y += t.height() + _ENTRE


def _tronquer():
    """Limite le nombre de notifications affichees simultanement."""
    while len(_VISIBLES) >= _MAX_VISIBLES:
        t = _VISIBLES.pop(0)
        try:
            t.close()
            t.deleteLater()
        except RuntimeError:
            pass


class _Toast(QFrame):
    def __init__(self, ancre, texte, type_):
        super().__init__(None)
        self._ancre = ancre
        fg, bg = _TYPES.get(type_, _TYPES["info"])

        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)

        ombre = QGraphicsDropShadowEffect(self)
        ombre.setBlurRadius(28)
        ombre.setOffset(0, 6)
        ombre.setColor(QColor(20, 24, 34, 90))
        self.setGraphicsEffect(ombre)

        pastille = QFrame()
        pastille.setFixedSize(10, 10)
        pastille.setStyleSheet(
            f"QFrame {{ background: {fg}; border: none; border-radius: 5px; }}")

        label = QLabel(str(texte))
        label.setWordWrap(True)
        label.setMinimumWidth(240)
        label.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; font-weight: 600;"
            " background: transparent; border: none; padding: 2px;")

        h = QHBoxLayout(self)
        h.setContentsMargins(18, 12, 18, 12)
        h.setSpacing(12)
        h.addWidget(pastille, 0, Qt.AlignTop)
        h.addWidget(label, 1)
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1px solid {C_BORDER};"
            " border-radius: 12px; }}")

        self.adjustSize()
        self.setMinimumWidth(_TAILLE_MIN)
        self.setMaximumWidth(_TAILLE_MAX)
        self.setWindowOpacity(0.0)

    def _demarrer(self, duree):
        self.show()
        depart = self._cible_x + 40
        self._glisser_vers(self._cible_x, 260, depart=depart)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(260)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(anim.deleteLater)
        self._anim_op = anim
        anim.start()
        QTimer.singleShot(duree, self._fermer)

    def _glisser_vers(self, arrivee_x, ms, depart=None):
        if depart is None:
            depart = self.pos().x()
        if abs(depart - arrivee_x) < 1:
            return
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(ms)
        anim.setStartValue(QPoint(int(depart), int(self.pos().y())))
        anim.setEndValue(QPoint(int(arrivee_x), int(self.pos().y())))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(anim.deleteLater)
        self._anim_pos = anim
        anim.start()

    def _fermer(self):
        if self not in _VISIBLES:
            self._detruire()
            return
        _VISIBLES.remove(self)
        ancre = self._ancre
        self._glisser_vers(self.pos().x() + 90, 240, depart=self.pos().x())
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(240)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(anim.deleteLater)
        self._anim_out = anim
        anim.start()
        QTimer.singleShot(260, self._detruire)
        _repositionner(ancre, anime=True)

    def _detruire(self):
        try:
            self.close()
            self.deleteLater()
        except RuntimeError:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._fermer()
        super().mousePressEvent(event)