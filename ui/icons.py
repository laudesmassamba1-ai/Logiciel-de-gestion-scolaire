"""Jeu d'icones vectorielles maison (aucune dependance externe).

Toutes les icones sont dessinees au `QPainter` sur une grille 24x24, en
traits arrondis (style Apple minimal), avec une seule couleur d'accent.
Elles restent nettes sur ecrans HiDPI (rendu au devicePixelRatio reel) et
se mettent en cache par (nom, couleur, taille, dpr).

API :
    icone("eleves", couleur=Colors.TEXT_MUTED, taille=18)  -> QIcon
    pixmap("caisse", couleur=Colors.PRIMARY, taille=24)    -> QPixmap

Utiliser ces icones partout ou l'app affichait `fa5s.*` : sidebar,
en-tetes de page, cartes KPI, etats vides, boutons d'action.
"""

from __future__ import annotations

from functools import lru_cache

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, \
    QPolygonF

from resources.design_tokens import Colors

_GRILLE = 24.0
_TRAIT = 1.8


def _pen(p, couleur):
    stylo = QPen(QColor(couleur), _TRAIT)
    stylo.setCapStyle(Qt.RoundCap)
    stylo.setJoinStyle(Qt.RoundJoin)
    p.setPen(stylo)
    p.setBrush(Qt.NoBrush)
    return stylo


def _ligne(p, x1, y1, x2, y2):
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _rond(p, cx, cy, r):
    p.drawEllipse(QPointF(cx, cy), r, r)


def _rect(p, x, y, w, h, r=2.0):
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _poly(p, *points):
    p.drawPolyline(QPolygonF(list(points)))


# ---------------------------------------------------------------------------
# Dessins (grille 24x24). Chaque fonction recoit le QPainter deja cale.
# ---------------------------------------------------------------------------
def _dashboard(p):
    for x, y in ((3, 3), (14, 3), (3, 14), (14, 14)):
        _rect(p, x, y, 7, 7, 2.2)


def _stats(p):
    p.setBrush(p.pen().color())
    for x, y, h in ((4, 13, 7), (10, 8, 12), (16, 4, 16)):
        _rect(p, x, y, 4, h, 1.6)
    p.setBrush(Qt.NoBrush)


def _eleves(p):
    _rond(p, 12, 8, 3.2)
    chemin = QPainterPath()
    chemin.moveTo(5.5, 19.5)
    chemin.arcTo(QRectF(5.5, 12.5, 13, 13), 0, 180)
    p.drawPath(chemin)
    _ligne(p, 8, 5.4, 16, 5.4)


def _caisse(p):
    _rect(p, 3, 6, 18, 12, 2.6)
    _ligne(p, 3, 10, 21, 10)
    p.setBrush(p.pen().color())
    _rond(p, 17, 14, 1.1)
    p.setBrush(Qt.NoBrush)


def _tarifs(p):
    chemin = QPainterPath()
    chemin.moveTo(12, 3)
    chemin.lineTo(21, 12)
    chemin.lineTo(12, 21)
    chemin.lineTo(3, 12)
    chemin.closeSubpath()
    p.drawPath(chemin)
    _rond(p, 8.5, 8.5, 1.3)


def _paiements(p):
    p.drawEllipse(QPointF(12, 8), 6.5, 3.2)
    _ligne(p, 5.5, 8, 5.5, 12)
    _ligne(p, 18.5, 8, 18.5, 12)
    chemin = QPainterPath()
    chemin.moveTo(5.5, 12)
    chemin.arcTo(QRectF(5.5, 8.8, 13, 6.4), 180, 180)
    p.drawPath(chemin)


def _classes(p):
    chemin = QPainterPath()
    chemin.moveTo(3, 10)
    chemin.lineTo(12, 4)
    chemin.lineTo(21, 10)
    p.drawPath(chemin)
    _rect(p, 5, 11, 14, 8, 1.6)
    _rect(p, 10, 14, 4, 5, 1.2)


def _cycles(p):
    chemin = QPainterPath()
    chemin.moveTo(5, 9)
    chemin.cubicTo(5, 4.5, 19, 4.5, 19, 9)
    p.drawPath(chemin)
    p.drawPolyline(QPointF(16.5, 6.5), QPointF(19, 9), QPointF(16.5, 11.5))
    chemin2 = QPainterPath()
    chemin2.moveTo(19, 15)
    chemin2.cubicTo(19, 19.5, 5, 19.5, 5, 15)
    p.drawPath(chemin2)
    p.drawPolyline(QPointF(7.5, 12.5), QPointF(5, 15), QPointF(7.5, 17.5))


def _notes(p):
    _rect(p, 5, 4, 14, 17, 2.4)
    _rect(p, 9, 2.5, 6, 3, 1.2)
    for y in (10, 13, 16):
        _ligne(p, 8, y, 16, y)


def _presences(p):
    _rect(p, 3.5, 5, 17, 15, 2.6)
    _ligne(p, 3.5, 9.5, 20.5, 9.5)
    _ligne(p, 8, 3.5, 8, 6.5)
    _ligne(p, 16, 3.5, 16, 6.5)
    p.drawPolyline(QPointF(8.5, 14.5), QPointF(11, 17), QPointF(16, 12))


def _planning(p):
    _rect(p, 3.5, 5, 17, 15, 2.6)
    _ligne(p, 3.5, 9.5, 20.5, 9.5)
    _ligne(p, 8, 3.5, 8, 6.5)
    _ligne(p, 16, 3.5, 16, 6.5)
    for x in (8, 12.5, 17):
        _ligne(p, x, 12.5, x, 17)


def _personnel(p):
    _rond(p, 9, 8, 3)
    chemin = QPainterPath()
    chemin.moveTo(3, 19)
    chemin.arcTo(QRectF(3, 12, 12, 13), 0, 180)
    p.drawPath(chemin)
    _rond(p, 17, 8.5, 2.4)


def _programmes(p):
    _rect(p, 4, 4, 16, 16, 2.4)
    _ligne(p, 12, 4, 12, 20)
    for y in (8, 11, 14, 17):
        _ligne(p, 6, y, 10, y)
        _ligne(p, 14, y, 18, y)


def _parametres(p):
    _rond(p, 12, 12, 3.2)
    import math
    for i in range(8):
        a = math.pi / 4 * i
        cx, cy = 12 + math.cos(a) * 6.2, 12 + math.sin(a) * 6.2
        _rond(p, cx, cy, 1.15)


def _comptes(p):
    chemin = QPainterPath()
    chemin.moveTo(12, 3)
    chemin.lineTo(20, 6)
    chemin.lineTo(20, 12)
    chemin.cubicTo(20, 17, 16, 20, 12, 21.5)
    chemin.cubicTo(8, 20, 4, 17, 4, 12)
    chemin.lineTo(4, 6)
    chemin.closeSubpath()
    p.drawPath(chemin)
    _rond(p, 12, 10.5, 1.8)
    _ligne(p, 12, 12.3, 12, 15)


def _bloc_notes(p):
    chemin = QPainterPath()
    chemin.moveTo(5, 3.5)
    chemin.lineTo(14, 3.5)
    chemin.lineTo(19, 8.5)
    chemin.lineTo(19, 20.5)
    chemin.lineTo(5, 20.5)
    chemin.closeSubpath()
    p.drawPath(chemin)
    p.drawPolyline(QPointF(14, 3.5), QPointF(14, 8.5), QPointF(19, 8.5))
    for y in (12, 15):
        _ligne(p, 8, y, 16, y)


def _calendrier(p):
    _rect(p, 3.5, 5, 17, 15, 2.6)
    _ligne(p, 3.5, 9.5, 20.5, 9.5)
    _ligne(p, 8, 3.5, 8, 6.5)
    _ligne(p, 16, 3.5, 16, 6.5)
    p.setBrush(p.pen().color())
    for x in (7, 12, 17):
        for y in (13, 16):
            _rond(p, x, y, 0.9)
    p.setBrush(Qt.NoBrush)


def _documents(p):
    p.drawPolyline(QPointF(3.5, 7), QPointF(9, 7), QPointF(11, 4.5),
                   QPointF(20.5, 4.5), QPointF(20.5, 19.5), QPointF(3.5, 19.5),
                   QPointF(3.5, 7))


def _reseau(p):
    _rond(p, 12, 6, 2.4)
    _rond(p, 6, 17, 2.4)
    _rond(p, 18, 17, 2.4)
    _ligne(p, 10.7, 8.1, 7.3, 14.9)
    _ligne(p, 13.3, 8.1, 16.7, 14.9)
    _ligne(p, 8.4, 17, 15.6, 17)


def _rapports(p):
    _rect(p, 5.5, 3.5, 13, 17, 2.2)
    _ligne(p, 9, 15.5, 9, 12)
    _ligne(p, 12, 15.5, 12, 8.5)
    _ligne(p, 15, 15.5, 15, 10.5)


def _assistant(p):
    chemin = QPainterPath()
    chemin.moveTo(12, 3)
    chemin.lineTo(13.8, 9.2)
    chemin.lineTo(20, 11)
    chemin.lineTo(13.8, 12.8)
    chemin.lineTo(12, 19)
    chemin.lineTo(10.2, 12.8)
    chemin.lineTo(4, 11)
    chemin.lineTo(10.2, 9.2)
    chemin.closeSubpath()
    p.drawPath(chemin)


def _add(p):
    _ligne(p, 12, 5, 12, 19)
    _ligne(p, 5, 12, 19, 12)


def _edit(p):
    chemin = QPainterPath()
    chemin.moveTo(5, 19)
    chemin.lineTo(6, 15)
    chemin.lineTo(15.5, 5.5)
    chemin.lineTo(18.5, 8.5)
    chemin.lineTo(9, 18)
    chemin.closeSubpath()
    p.drawPath(chemin)
    _ligne(p, 14, 7, 17, 10)


def _delete(p):
    _ligne(p, 4.5, 6.5, 19.5, 6.5)
    _ligne(p, 9.5, 6.5, 9.5, 4)
    _ligne(p, 14.5, 6.5, 14.5, 4)
    _ligne(p, 9.5, 4, 14.5, 4)
    p.drawPolyline(QPointF(6.5, 6.5), QPointF(7.5, 20), QPointF(16.5, 20),
                   QPointF(17.5, 6.5))
    _ligne(p, 10.5, 10, 10.5, 17)
    _ligne(p, 13.5, 10, 13.5, 17)


def _search(p):
    _rond(p, 10.5, 10.5, 6)
    _ligne(p, 15, 15, 20, 20)


def _export(p):
    _ligne(p, 12, 3.5, 12, 14.5)
    p.drawPolyline(QPointF(8, 10.5), QPointF(12, 14.5), QPointF(16, 10.5))
    p.drawPolyline(QPointF(5, 16), QPointF(5, 20.5), QPointF(19, 20.5),
                   QPointF(19, 16))


def _save(p):
    _rect(p, 4, 4, 16, 16, 2.4)
    _rect(p, 8, 4, 8, 5.5, 1)
    _rect(p, 7.5, 13, 9, 7, 1.4)


def _print(p):
    _ligne(p, 7, 9, 7, 4.5)
    _ligne(p, 7, 4.5, 17, 4.5)
    _ligne(p, 17, 4.5, 17, 9)
    _rect(p, 3.5, 9, 17, 8, 2.2)
    _rect(p, 7, 14.5, 10, 5.5, 1.2)


def _close(p):
    _ligne(p, 6, 6, 18, 18)
    _ligne(p, 18, 6, 6, 18)


def _check(p):
    p.drawPolyline(QPointF(4.5, 12.5), QPointF(10, 18), QPointF(19.5, 6))


def _user(p):
    _rond(p, 12, 8, 3.4)
    chemin = QPainterPath()
    chemin.moveTo(4.5, 20)
    chemin.arcTo(QRectF(4.5, 12.5, 15, 15), 0, 180)
    p.drawPath(chemin)


def _money(p):
    _rond(p, 12, 12, 8.5)
    _ligne(p, 12, 7, 12, 17)
    chemin = QPainterPath()
    chemin.moveTo(14.5, 9)
    chemin.cubicTo(10, 9, 10, 12, 14.5, 12)
    chemin.cubicTo(10, 12, 10, 15, 14.5, 15)
    p.drawPath(chemin)


def _filter(p):
    chemin = QPainterPath()
    chemin.moveTo(3.5, 5)
    chemin.lineTo(20.5, 5)
    chemin.lineTo(14, 12.5)
    chemin.lineTo(14, 20)
    chemin.lineTo(10, 18)
    chemin.lineTo(10, 12.5)
    chemin.closeSubpath()
    p.drawPath(chemin)


def _mort(p):
    _rect(p, 4, 4, 16, 16, 3)


def _map(p):
    chemin = QPainterPath()
    chemin.moveTo(12, 3.5)
    chemin.cubicTo(7, 3.5, 4.5, 7.5, 4.5, 11.3)
    chemin.cubicTo(4.5, 16.5, 12, 20.5, 12, 20.5)
    chemin.cubicTo(12, 20.5, 19.5, 16.5, 19.5, 11.3)
    chemin.cubicTo(19.5, 7.5, 17, 3.5, 12, 3.5)
    p.drawPath(chemin)
    _rond(p, 12, 11, 2.2)


def _award(p):
    _ligne(p, 12, 4, 12, 12)
    _rond(p, 12, 15.5, 4)
    _poly(p, 9.8, 14.4, 7.5, 20.5, 12, 18, 16.5, 20.5, 14.2, 14.4)


def _tag(p):
    _rect(p, 3.5, 7, 14, 10.5, 2.4)
    _ligne(p, 8, 3.5, 8, 21)
    _rond(p, 13, 12.2, 1.4)


_DESSINS = {
    "dashboard": _dashboard,
    "stats": _stats,
    "eleves": _eleves,
    "caisse": _caisse,
    "tarifs": _tarifs,
    "paiements": _paiements,
    "classes": _classes,
    "cycles": _cycles,
    "notes": _notes,
    "presences": _presences,
    "planning": _planning,
    "personnel": _personnel,
    "programmes": _programmes,
    "parametres": _parametres,
    "comptes": _comptes,
    "bloc_notes": _bloc_notes,
    "calendrier": _calendrier,
    "documents": _documents,
    "reseau": _reseau,
    "rapports": _rapports,
    "assistant": _assistant,
    "add": _add,
    "edit": _edit,
    "delete": _delete,
    "search": _search,
    "export": _export,
    "save": _save,
    "print": _print,
    "close": _close,
    "check": _check,
    "user": _user,
    "money": _money,
    "filter": _filter,
    "map": _map,
    "award": _award,
    "tag": _tag,
}

# Alias pratiques
_DESSINS["plus"] = _add
_DESSINS["pdf"] = _export
_DESSINS["tresorerie"] = _money
_DESSINS["refresh"] = _cycles


@lru_cache(maxsize=512)
def pixmap(nom, couleur=Colors.TEXT_MUTED, taille=24, dpr=1.0):
    """Renvoie un QPixmap net (rendu au dpr reel)."""
    dpr = max(1.0, float(dpr))
    px = max(8, int(round(taille * dpr)))
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(px / _GRILLE, px / _GRILLE)
    _pen(p, couleur)
    dessin = _DESSINS.get(nom, _mort)
    try:
        dessin(p)
    except Exception:
        _mort(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icone(nom, couleur=Colors.TEXT_MUTED, taille=24):
    """Renvoie un QIcon utilisable sur boutons, listes, en-tetes."""
    return QIcon(pixmap(nom, couleur=couleur, taille=taille))


def pixmap_icone(nom, couleur=Colors.TEXT_MUTED, taille=24, widget=None):
    """QPixmap au devicePixelRatio du widget (net sur ecran HiDPI)."""
    from resources.cel_engine import dpr_reel
    dpr = dpr_reel(widget) if widget is not None else 1.0
    return pixmap(nom, couleur=couleur, taille=taille, dpr=dpr)
