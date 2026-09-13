"""Tests de la confirmation française ui/pages/helpers.confirmer() :
boutons « Oui / Non », bouton par défaut « Non » (pivot sûr pour les
actions destructrices), et résultat sur clic.

La structure de la boîte (boutons + défaut) est inspectée SANS boucle
modale (construction via helpers._boite_confirmer) : c'est fiable partout,
y compris en offscreen. Les tests qui cliquent réellement dans la boîte
modale sont réservés à Linux, la boucle exec_() d'un QMessageBox pouvant
provoquer une « access violation » sous l'environnement offscreen de la CI
Windows."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def _boite(texte, titre="Titre de test"):
    from PyQt5.QtWidgets import QWidget
    from ui.pages import helpers as H

    parent = QWidget()
    return H._boite_confirmer(parent, texte, titre), parent


def test_boutons_francais_et_defaut_non(app):
    """Boutons « Oui / Non » en français, défaut « Non » : vérifié sans
    ouvrir la boîte (aucune boucle modale, aucun risque de plantage)."""
    (boite, oui), parent = _boite("Supprimer ?")
    try:
        assert sorted(b.text() for b in boite.buttons()) == ["Non", "Oui"]
        assert boite.defaultButton().text() == "Non"
        assert boite.buttonRole(oui) == boite.YesRole  # rôle Yes mémorisé
    finally:
        boite.deleteLater()
        parent.deleteLater()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="QMessageBox.exec_() en offscreen sous CI Windows "
           "peut lever une access violation",
)
def test_clic_non_retourne_faux(app):
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication, QWidget
    from ui.pages import helpers as H

    resultat = {}

    def cliquer():
        bois = QApplication.activeModalWidget()
        for bt in bois.buttons():
            if bt.text() == "Non":
                bt.click()
                return

    QTimer.singleShot(40, cliquer)
    resultat["val"] = H.confirmer(QWidget(), "Supprimer ?", "Titre de test")
    app.processEvents()
    assert resultat["val"] is False


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="QMessageBox.exec_() en offscreen sous CI Windows "
           "peut lever une access violation",
)
def test_clic_oui_retourne_vrai(app):
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication, QWidget
    from ui.pages import helpers as H

    resultat = {}

    def cliquer():
        bois = QApplication.activeModalWidget()
        for bt in bois.buttons():
            if bt.text() == "Oui":
                bt.click()
                return

    QTimer.singleShot(40, cliquer)
    resultat["val"] = H.confirmer(QWidget(), "Supprimer ?", "Titre de test")
    app.processEvents()
    assert resultat["val"] is True