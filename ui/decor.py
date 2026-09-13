"""Decoration du theme : avatar circulaire des utilisateurs.

(Le systeme de « FondBulle » aux cercles flottants a ete retire : il
rendait des formes decoratives non coherentes avec le contenu.)
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel

from core.config import C_GRAD_TOP, C_GRAD_BOTTOM


def creer_avatar(nom_complet, taille=42):
    """Avatar circulaire or : les initiales du nom sur un degrade or avec
    un petit pied (effet« 3D douce »)."""
    initiales = "".join(
        part[0].upper() for part in str(nom_complet or "?").split() if part
    )[:2] or "?"
    lbl = QLabel(initiales)
    lbl.setFixedSize(taille, taille)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFont(QFont("Inter", max(9, int(taille * 0.34)), QFont.Bold))
    lbl.setStyleSheet(
        f"QLabel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
        f" stop:0 {C_GRAD_TOP}, stop:1 {C_GRAD_BOTTOM}); color: #FFFFFF;"
        f" border: 3px solid #9A7007; border-radius: {taille // 2}px; }}")
    return lbl