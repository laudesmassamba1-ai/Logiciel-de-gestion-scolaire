"""Smoke tests des graphiques : courbes multi-couleurs (SimpleLineChart)
et page Statistiques. Les graphiques sont peints en QPainter : on
verifie leur construction ET leur rendu sans crash."""

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


def _peindre(widget, largeur=640, hauteur=320):
    """Rend le widget dans une image : l'absence d'exception prouve que
    paintEvent (grid, polylines, legende) ne plante pas."""
    from PyQt5.QtGui import QImage, QPainter
    img = QImage(largeur, hauteur, QImage.Format_ARGB32)
    img.fill(0xFFFFFFFF)
    painter = QPainter(img)
    widget.resize(largeur, hauteur)
    widget.render(painter)
    painter.end()
    return img


def test_ligne_unique_avec_legende(app):
    from ui.widgets import SimpleLineChart
    chart = SimpleLineChart(titre="Tresorerie")
    chart.set_series([("Recettes", [0, 5000, 12000, 8000])],
                     ["Sep", "Oct", "Nov", "Dec"])
    img = _peindre(chart)
    assert not img.isNull()


def test_deux_lignes_series_distinctes(app):
    from ui.widgets import SimpleLineChart
    chart = SimpleLineChart(titre="Recettes / Depenses")
    chart.set_series([("Recettes", [1000, 9000, 15000, 20000]),
                      ("Depenses", [8000, 7000, 4000, 6000])],
                     ["Sep", "Oct", "Nov", "Dec"])
    _peindre(chart)
    # Les deux series sont conservees, chaque valeur numerique.
    assert len(chart.series) == 2
    assert chart.series[0][1] == [1000.0, 9000.0, 15000.0, 20000.0]


def test_graphe_vide_ne_plante_pas(app):
    from ui.widgets import SimpleLineChart
    chart = SimpleLineChart(titre="")
    _peindre(chart)
    chart.set_series([("A", [1, 2])], ["x", "y"])
    _peindre(chart)


def test_page_statistiques_construit_le_graphe(app):
    from database import db
    db.init_db()
    from PyQt5.QtWidgets import QWidget
    from ui.pages.statistiques_page import statistiques
    page = QWidget()
    ctx = type("Ctx", (), {"user": {"role": "directeur"}})()
    page.refresh = None
    statistiques(page, ctx)
    app.processEvents()
    from ui.widgets import SimpleLineChart
    found = page.findChildren(SimpleLineChart)
    assert found, "le graphe a lignes doit etre present dans Statistiques"
    _peindre(found[0])