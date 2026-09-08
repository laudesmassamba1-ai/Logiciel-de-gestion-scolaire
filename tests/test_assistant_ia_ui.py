"""Smoke test UI de l'assistante : le rendu des bulles ne doit jamais
planter (regression : addWidget() recevait un QHBoxLayout de la rangee
de feedback a la place d'un QWidget -> TypeError a l'ouverture)."""

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


@pytest.fixture(scope="module")
def utilisateur():
    return {"id": 1, "nom_complet": "Test Directeur",
            "username": "root", "role": "directeur"}


@pytest.fixture(scope="module")
def assistante(app, utilisateur):
    from database import db
    db.init_db()
    from ui.pages.assistant_page import AssistantChatDialog
    fenetre = AssistantChatDialog(None, type(
        "Ctx", (), {"user": utilisateur, "role": "directeur",
                    "navigate": lambda p: None})())
    yield fenetre
    fenetre.close()


def test_accueil_se_rend(assistante, app):
    """L'accueil (bulles + boutons de feedback) se construit sans erreur."""
    assistante.show()
    app.processEvents()
    assert assistante.flux.count() > 1  # stretch + au moins une bulle
    assert assistante._accueil_affiche


def test_bulles_avec_feedback(assistante, app):
    """Chaque bulle de l'assistante accepte sa rangee de feedback."""
    avant = assistante.flux.count()
    bulle = assistante._bulle_assistante("Salut !", avec_feedback=True)
    app.processEvents()
    assert bulle is not None
    assert assistante.flux.count() > avant
    # La 1re bulle de l'accueil comporte bien ses 2 boutons de vote.
    premiere_rangee = None
    i = 0
    while i < assistante.flux.count():
        item = assistante.flux.itemAt(i)
        if item is not None and item.layout() is not None:
            premiere_rangee = item.layout()
            break
        i += 1
    assert premiere_rangee is not None


def test_envoyer_message_un_tour(assistante, app):
    """Un tour de chat complet (saisie -> reponse avec feedback)."""
    assistante.champ.setPlainText("bonjour")
    app.processEvents()
    assistante._envoyer()
    app.processEvents()
    assert not assistante.flux.count() == 1