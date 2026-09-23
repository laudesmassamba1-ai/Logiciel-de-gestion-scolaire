"""Photos des eleves.

Une photo complete le profil de l'eleve (affichage dans le dossier
d'inscription). Elle est STOCKEE LOCALEMENT (dossier `data/photos/`) et
seul le nom du fichier est garde dans la colonne `eleves.photo`. Elle n'est
volontairement PAS synchronisee : le serveur et les autres postes n'ont pas
cette colonne, et le pull (upsert additif) ne la touche jamais.
"""

import re

from core.config import data_dir
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QBrush

PHOTO_DIR = data_dir() / "photos"

TAILLE_MAX = 640


def _nom_fichier(matricule):
    propre = re.sub(r"[^A-Za-z0-9]+", "_", str(matricule or "")).strip("_")
    if not propre:
        propre = "eleve"
    return f"eleve_{propre}.jpg"


def chemin_photo(eleve):
    """Chemin absolu de la photo si le fichier existe, sinon None."""
    if not eleve or not eleve.get("photo"):
        return None
    p = PHOTO_DIR / eleve["photo"]
    return str(p) if p.exists() else None


def pixmap_photo(eleve):
    chemin = chemin_photo(eleve)
    if not chemin:
        return None
    pix = QPixmap(chemin)
    return pix if not pix.isNull() else None


def pixmap_rond(pix, diametre=114):
    """Recadre `pix` en cercle de `diametre` px (fond transparent).

    La photo est mise a l'echelle par expansion puis recadree au centre :
    une image non carree (ex. 159x148) remplit proprement le rond, sans
    debordement ni deformation, et sans coins carres visibles.
    """
    d = int(diametre)
    if pix is None or pix.isNull():
        return QPixmap(d, d)
    p = pix.scaled(d, d, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    if p.width() > d or p.height() > d:
        x = (p.width() - d) // 2
        y = (p.height() - d) // 2
        p = p.copy(x, y, d, d)
    rond = QPixmap(d, d)
    rond.fill(Qt.transparent)
    painter = QPainter(rond)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(p))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, d, d)
    painter.end()
    return rond


def sauvegarder_photo(source, matricule):
    """Copie une image choisie par l'utilisateur dans `data/photos/`,
    redimensionnee au besoin. Renvoie le nom court du fichier enregistre."""
    pix = QPixmap(source)
    if pix.isNull():
        raise ValueError("Le fichier choisi ne peut pas etre lu comme une "
                         "image (PNG, JPG, BMP, GIF...).")
    if max(pix.width(), pix.height()) > TAILLE_MAX:
        pix = pix.scaled(TAILLE_MAX, TAILLE_MAX, Qt.KeepAspectRatio,
                         Qt.SmoothTransformation)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    nom = _nom_fichier(matricule)
    if not pix.save(str(PHOTO_DIR / nom), "JPG", 88):
        raise ValueError("L'enregistrement de la photo a echoue.")
    return nom