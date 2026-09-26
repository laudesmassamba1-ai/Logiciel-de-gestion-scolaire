"""Configuration globale des tests.

Désactive le backend LLM (ollama) par défaut pendant les tests pour garder
les tests rapides, reproductibles et sans dépendance externe.

Pour exécuter des tests qui nécessitent le LLM réel, utilisez :
    pytest --llm
"""
import pytest


def pytest_addoption(parser):
    parser.addoption("--llm", action="store_true", default=False,
                     help="Activer les appels au backend LLM (ollama) pendant les tests")


@pytest.fixture(autouse=True)
def _desactiver_llm(monkeypatch, pytestconfig, request):
    if pytestconfig.getoption("--llm"):
        return
    if "test_llm_backend" in request.module.__name__:
        return
    from services.ia.llm_backend import LLMBackend
    monkeypatch.setattr(LLMBackend, "disponible", lambda self: False)
    monkeypatch.setattr(LLMBackend, "_generer", lambda self, msgs: "")
    # Neutralise la recherche web pendant les tests (le module
    # test_webrecherche.py mocke urllib lui-meme).
    if "test_webrecherche" not in request.module.__name__:
        from services.ia.webrecherche import RechercheWeb
        monkeypatch.setattr(RechercheWeb, "disponible", lambda self: False)
