"""Smoke test : la page Parametres construit bien ses onglets.

Regression : le regroupement du contenu en onglets (re-parenting des
groupes/cartes du scroll vers un QTabWidget) ne doit jamais planter, et
doit produire 3 onglets (Etablissement, Appreciations, Systeme)."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


@pytest.fixture()
def base(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)
    monkeypatch.setenv("GS_DATA_DIR", str(data))
    import database.db
    db_module = sys.modules["database.db"]
    monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
    monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
    from database import db
    db._initialized = False
    db.init_db()
    yield db
    db._initialized = False


USER_DIRECTEUR = {"id": 7, "role": "directeur", "nom_complet": "Test Dir",
                  "username": "dir"}


class TestParametresOnglets:
    def test_la_page_construit_trois_onglets(self, app, base):
        from PyQt5.QtWidgets import QTabWidget, QWidget

        from ui.pages.helpers import PageContext
        from ui.pages.parametres_page import parametres

        page = QWidget()
        ctx = PageContext(USER_DIRECTEUR, lambda *a: None)
        parametres(page, ctx)

        tabs = page.findChild(QTabWidget, "ongletsParams")
        assert tabs is not None
        assert tabs.count() == 3
        noms = [tabs.tabText(i) for i in range(tabs.count())]
        assert "Etablissement" in noms
        assert "Appreciations" in noms
        assert "Systeme" in noms

    def test_re_parenting_changed_parent_of_groupes(self, app, base):
        from PyQt5.QtWidgets import QTabWidget, QWidget

        from ui.pages.helpers import PageContext
        from ui.pages.parametres_page import parametres

        page = QWidget()
        ctx = PageContext(USER_DIRECTEUR, lambda *a: None)
        parametres(page, ctx)

        tabs = page.findChild(QTabWidget, "ongletsParams")
        # Le groupe backup a ete deplace du scroll vers un onglet : on
        # remonte la chaine de parents jusqu'aux onglets (QTabWidget enveloppe
        # un QStackedWidget, la page est donc 2 niveaux plus bas).
        courant = page.backup_group.parentWidget()
        atteint = False
        for _ in range(4):
            if courant is tabs:
                atteint = True
                break
            courant = courant.parentWidget() if courant is not None else None
        assert atteint