"""Regression visuelle des fenetres et dialogues.

Verifie deux invariants sur les ecrans de connexion et l'assistant
multi-postes : (1) le contenu tient dans la fenetre (rien n'est coupe),
(2) la fenetre ne depasse jamais l'ecran disponible. Ainsi que le helper
_adapter_hauteur utilise par les dialogues (classe, compte, personnel...).
"""

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
def _base():
    import tempfile
    tmp = tempfile.mkdtemp()
    os.environ["GS_DATA_DIR"] = tmp
    return tmp


def expected_height(layout, screen_height):
    besoin = max(layout.sizeHint().height(), layout.minimumSize().height())
    dispo = screen_height - 48
    return min(besoin, max(dispo, 360))


def test_adaptateur_hauteur_agrandit_le_dialogue(app):
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget
    from ui.pages.helpers import _adapter_hauteur
    dlg = QDialog()
    dlg.resize(400, 200)
    lay = QVBoxLayout(dlg)
    corps = QWidget()
    corps.setMinimumHeight(420)
    lay.addWidget(corps)
    dlg.show()
    app.processEvents()
    _adapter_hauteur(dlg)
    app.processEvents()
    dispo = app.primaryScreen().availableGeometry().height() - 48
    assert dlg.height() == expected_height(dlg.layout(), dispo + 48)
    assert dlg.height() > 200


def test_adaptateur_hauteur_ne_depasse_pas_l_ecran(app):
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget
    from ui.pages.helpers import _adapter_hauteur
    dlg = QDialog()
    dlg.resize(400, 200)
    lay = QVBoxLayout(dlg)
    corps = QWidget()
    corps.setFixedSize(100, 2000)
    lay.addWidget(corps)
    dlg.show()
    app.processEvents()
    _adapter_hauteur(dlg)
    app.processEvents()
    dispo = app.primaryScreen().availableGeometry().height() - 64
    assert dlg.height() == dispo
    assert dlg.height() <= app.primaryScreen().availableGeometry().height()


def test_login_carte_dans_la_fenetre(app):
    from ui.login_view import LoginDialog
    dlg = LoginDialog()
    dlg.show()
    app.processEvents()
    carte = dlg.card
    bas = carte.mapTo(dlg, carte.rect().topLeft()).y() + carte.height()
    assert bas <= dlg.height()
    assert dlg.height() <= app.primaryScreen().availableGeometry().height()
    dlg.close()


def test_setup_carte_dans_la_fenetre(app):
    from ui.login_view import FirstSetupDialog
    dlg = FirstSetupDialog()
    dlg.show()
    app.processEvents()
    carte = dlg.card
    bas = carte.mapTo(dlg, carte.rect().topLeft()).y() + carte.height()
    assert bas <= dlg.height()
    assert dlg.height() <= app.primaryScreen().availableGeometry().height()
    dlg.close()


def test_assistant_serveur_contenu_scrollable(app):
    from PyQt5.QtWidgets import QPushButton, QScrollArea
    from ui.assistant_serveur import AssistantServeur
    dlg = AssistantServeur()
    dlg.show()
    app.processEvents()
    defile = dlg.findChild(QScrollArea)
    assert defile is not None
    barre = defile.verticalScrollBar()
    assert barre.maximum() > 0
    barre.setValue(barre.maximum())
    app.processEvents()
    boutons = [b for b in dlg.findChildren(QPushButton) if "Fermer" in b.text()]
    assert boutons
    pos = boutons[0].mapTo(dlg, boutons[0].rect().topLeft()).y()
    assert 0 <= pos <= dlg.height()
    dlg.close()