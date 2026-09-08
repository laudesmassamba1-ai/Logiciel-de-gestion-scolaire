"""Micro-animations et transitions (overhaul visuel session 2026-09-09).

Petite boite a outils 100 % PyQt5 (sans dependance) pour rendre
l'interface plus vivante, coherente et « faite avec soin » :

- fade_in        : entree en fondu (transition de page principale)
- pop_in         : apparition ressort (fondu doux avec courbe out-back)
- stagger        : apparitions echelonnees (cartes KPI, blocs)
- bounce_pulse   : pulsation douce et discrete (badge « En Ligne »)
- hover_lift     : micro-elevation avec ombre douce au survol des
                   boutons de navigation (effet « carte »)

Regles :
- jamais d'animation qui bloque un flux metier ;
- durees courtes (160-450 ms), courbes ease-in-out/out-back ;
- chaque effet est nettoye quand il se termine pour ne pas degrader
  le rendu (setGraphicsEffect(None)) ;
- les helpers sont tolerants aux widgets deja detruits (fin d'app).
"""

from PyQt5.QtCore import QEasingCurve, QEvent, QObject, QParallelAnimationGroup, \
    QPropertyAnimation, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect

from core.config import C_INK


def _detruit(widget):
    try:
        widget.objectName()
        return False
    except RuntimeError:
        return True


def _purger(widget):
    """Supprime l'effet graphique quand l'animation est terminee."""
    try:
        widget.setGraphicsEffect(None)
    except RuntimeError:
        pass  # widget deja detruit (application en cours de fermeture)


def fade_in(widget, duree=240, debut=0.0):
    """Fondu simple (transition de page). Nettoye l'effet a la fin."""
    if _detruit(widget):
        return None
    effet = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effet)
    anim = QPropertyAnimation(effet, b"opacity", widget)
    anim.setDuration(duree)
    anim.setStartValue(debut)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.finished.connect(lambda: _purger(widget))
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def pop_in(widget, duree=360, delai=0):
    """Apparition ressort : progression de l'opacite sur courbe out-back."""
    if _detruit(widget):
        return None
    effet = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effet)
    anim = QPropertyAnimation(effet, b"opacity", widget)
    anim.setDuration(duree)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutBack if duree >= 320
                        else QEasingCurve.OutCubic)
    anim.finished.connect(lambda: _purger(widget))

    def _demarrer():
        try:
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        except RuntimeError:
            pass
    if delai:
        QTimer.singleShot(delai, _demarrer)
    else:
        _demarrer()
    return anim


def stagger(widgets, au_total=520, duree=340):
    """Echelonne des apparitions ressort sur une liste de widgets."""
    widgets = [w for w in widgets if w is not None]
    if not widgets:
        return
    pas = int(au_total / len(widgets))
    for i, w in enumerate(widgets):
        pop_in(w, duree=duree, delai=int(pas * i))


def bounce_pulse(widget, fois=2, duree=200):
    """Pulsation douce et discrete (clignotement de confirmation)."""
    if _detruit(widget):
        return None
    effet = widget.graphicsEffect()
    if not isinstance(effet, QGraphicsOpacityEffect):
        effet = QGraphicsOpacityEffect(widget)
        effet.setOpacity(1.0)
        widget.setGraphicsEffect(effet)
    groupe = QParallelAnimationGroup(widget)
    for _ in range(fois):
        anim = QPropertyAnimation(effet, b"opacity", widget)
        anim.setDuration(duree)
        anim.setStartValue(0.45)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        groupe.addAnimation(anim)
    groupe.finished.connect(lambda: _purger(widget))
    groupe.start()
    return groupe


class _LiftFiltre(QObject):
    """Micro-elevation au survol : l'ombre douce se deplie (blurRadius
    anime 0 -> 18) a l'entree de la souris et se replie a la sortie."""

    def __init__(self, bouton):
        super().__init__(bouton)
        self.bouton = bouton
        self._anim = None
        self._ombre = None
        bouton.installEventFilter(self)

    def _creer_ombre(self):
        hexa = C_INK.lstrip("#")
        r, g, b = (int(hexa[i:i + 2], 16) for i in (0, 2, 4))
        self._ombre = QGraphicsDropShadowEffect(self.bouton)
        self._ombre.setBlurRadius(0)
        self._ombre.setOffset(0, 2)
        self._ombre.setColor(QColor(r, g, b, 46))
        return self._ombre

    def _animer(self, ouverte):
        if _detruit(self.bouton):
            return
        if self._ombre is None:
            ombre = self._creer_ombre()
            self.bouton.setGraphicsEffect(ombre)
        ombre = self._ombre
        if self._anim is not None:
            self._anim.stop()
        anim = QPropertyAnimation(ombre, b"blurRadius", self.bouton)
        anim.setDuration(170)
        anim.setStartValue(ombre.blurRadius())
        anim.setEndValue(18.0 if ouverte else 0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _finir():
            if not ouverte:
                _purger(self.bouton)
                self._ombre = None
        anim.finished.connect(_finir)
        self._anim = anim
        anim.start()

    def eventFilter(self, source, event):
        if source is not self.bouton:
            return False
        t = event.type()
        if t == QEvent.Enter:
            self._animer(True)
        elif t == QEvent.Leave:
            self._animer(False)
        return False


def hover_lift(boutons):
    """Installe la micro-levitation sur une liste de boutons."""
    for bouton in boutons:
        _LiftFiltre(bouton)