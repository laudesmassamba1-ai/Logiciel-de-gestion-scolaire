"""Tests de la palette de commandes (ui/palette.py) : filtrage sans accent,
activation (signal `choisi`) et fermeture (`annule`)."""

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
def hote(app):
    from PyQt5.QtWidgets import QWidget
    w = QWidget()
    w.resize(1280, 800)
    w.show()
    app.processEvents()
    yield w
    w.close()


@pytest.fixture()
def palette(hote):
    from ui.palette import Palette
    entrées = [
        ("Eleves", "Inscription et dossiers", "eleves"),
        ("Notes et Bulletins", "Saisie des notes, moyennes, bulletins", "notes"),
        ("Personnel", "Gestion des employes", "personnel"),
    ]
    p = Palette(hote)
    p.maj_entrees(entrées)
    yield p
    if p.isVisible():
        p._fermer()


def test_filtre_insensible_a_la_casse_et_aux_accents(palette, app):
    palette.saisie.setText("Ele")
    app.processEvents()
    assert palette.liste.count() == 1
    assert "Eleves" in palette.liste.item(0).text()


def test_filtre_par_terme_du_conseil(palette, app):
    palette.saisie.setText("bulletins")
    app.processEvents()
    assert palette.liste.count() == 1
    assert "Notes" in palette.liste.item(0).text()


def test_activation_emet_la_cle(palette, app):
    recus = []
    palette.choisi.connect(recus.append)
    palette.saisie.setText("personnel")
    app.processEvents()
    palette._activer()
    app.processEvents()
    assert recus == ["personnel"]
    assert not palette.isVisible()


def test_fermeture_emet_annule(palette, app):
    recus = []
    palette.annule.connect(lambda: recus.append(True))
    palette.ouvrir()
    app.processEvents()
    palette._fermer()
    assert recus == [True]


def test_aucun_resultat_ne_plante_pas(palette, app):
    palette.saisie.setText("zzzzzz")
    app.processEvents()
    assert palette.liste.count() == 0
    palette._activer()
    app.processEvents()