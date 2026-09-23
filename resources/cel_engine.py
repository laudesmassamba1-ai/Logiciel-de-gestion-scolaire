"""cel_engine — rendu des cartes « Liquid Glass ».

Carte verre : fond en degrade vertical (blanc -> bleu glace), coins
UNIFORMES, hairline 1 px glacee, aucune ombre portee (le degradé de fond
de l'appli porte l'effet verre). Le sprite est pre-rendu a la resolution
REELLE de l'ecran (devicePixelRatio) puis cache par cle (taille, rayon,
dpr) : la hairline reste nette au pixel pres, meme sur ecran HiDPI.
"""

from __future__ import annotations

from functools import lru_cache

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap

from resources.design_tokens import Colors, Radius

_EPAISSEUR_FILE = 1


def dpr_reel(widget) -> float:
    """devicePixelRatio effectif d'un widget (net au pixel pres)."""
    try:
        return max(1.0, float(widget.devicePixelRatio()))
    except Exception:
        return 1.0


def dpr_dispositif(widget) -> float:
    """devicePixelRatio reel de l'ecran (peut différer du widget)."""
    return dpr_reel(widget)


@lru_cache(maxsize=256)
def sprite_carte(largeur, hauteur, rayon=Radius.LG, dpr=1.0):
    """Sprite d'une carte verre a coins uniformes et hairline 1 px.

    Le pixmap retourne porte son DPR : il est net au pixel pres quelle que
    soit la densite de l'ecran (projecteur 4K, DPR 1.5 / 2.0 compris).
    """
    dpr = max(1.0, float(dpr))
    w = max(8, int(round(largeur * dpr)))
    h = max(8, int(round(hauteur * dpr)))

    sprite = QPixmap(w, h)
    sprite.fill(Qt.transparent)

    p = QPainter(sprite)
    p.setRenderHint(QPainter.Antialiasing, True)

    ep = _EPAISSEUR_FILE * dpr
    demi = ep / 2.0
    rect = QRectF(demi, demi, w - ep, h - ep)
    rp = float(rayon) * dpr

    # Fond « verre » : degrade vertical blanc -> bleu glace très pâle.
    gradient = QLinearGradient(0, 0, 0, h - ep)
    gradient.setColorAt(0.0, QColor(Colors.BG_CARD))
    gradient.setColorAt(1.0, QColor("#F3F7FF"))
    p.setPen(Qt.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(rect, rp, rp)

    # Reflet superieur discret (esprit liquide) : liseré blanc lumineux.
    reflet = QLinearGradient(0, 0, 0, (h - ep) * 0.45)
    reflet.setColorAt(0.0, QColor(255, 255, 255, 110))
    reflet.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(reflet)
    p.drawRoundedRect(QRectF(demi + ep, demi + ep,
                             w - 3 * ep, (h - ep) * 0.45 - ep), rp - ep, rp - ep)

    pen = QPen(QColor(Colors.CONTOUR))
    pen.setWidthF(ep)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect, rp, rp)

    p.end()
    sprite.setDevicePixelRatio(dpr)
    return sprite


def carte_pour(widget, rayon=Radius.LG):
    """Sprite a la taille LOGIQUE du widget, au DPR reel du widget.

    A appeler dans le resizeEvent / apres premiere taille : le sprite
    est mis en cache par (taille, rayon, dpr) — aucun re-paint inutile.
    """
    dpr = dpr_reel(widget)
    w = max(16, widget.width())
    h = max(16, widget.height())
    return sprite_carte(w, h, rayon, dpr), dpr
