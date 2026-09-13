"""Tests des notifications in-app (ui/toast.py) : empilement, limite,
fermeture manuelle et API publique."""

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


@pytest.fixture()
def fenetre(app):
    from PyQt5.QtWidgets import QWidget
    w = QWidget()
    w.resize(1200, 800)
    w.show()
    app.processEvents()
    yield w
    import ui.toast as T
    for t in T._VISIBLES[:]:
        t._fermer()
    app.processEvents()
    w.close()


def test_pilule_s_affiche_et_s_empile(app, fenetre):
    import ui.toast as T
    T.afficher(fenetre, "Premiere", duree=100000)
    T.afficher(fenetre, "Seconde", duree=100000)
    app.processEvents()
    assert len(T._VISIBLES) == 2
    visibles = [t for t in T._VISIBLES if t.isVisible()]
    assert len(visibles) == 2
    xs = {t.pos().x() for t in T._VISIBLES}
    assert len(xs) == 1
    ys = [t.pos().y() for t in T._VISIBLES]
    assert ys == sorted(ys)


def test_limite_a_quatre_visibles(app, fenetre):
    import ui.toast as T
    for i in range(6):
        T.afficher(fenetre, str(i), duree=100000)
    app.processEvents()
    assert len(T._VISIBLES) <= 4


def test_deux_api_de_parametresaurus(app, fenetre):
    from ui import toast
    toast.succes(fenetre, "Enregistre")
    toast.info(fenetre, "Information")
    toast.erreur(fenetre, "Echec")
    app.processEvents()
    assert len(toast._VISIBLES) == 3