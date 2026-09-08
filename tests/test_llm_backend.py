"""Tests pour le backend LLM (ollama integration)."""
import json
from unittest.mock import MagicMock, patch
from services.ia.llm_backend import LLMBackend, get_backend


def _mock_response(models):
    """Crée un mock de réponse urlopen qui fonctionne comme context manager."""
    response = MagicMock()
    response.read.return_value = json.dumps({"models": models}).encode()
    response.__enter__.return_value = response
    response.__exit__.return_value = None
    return response


def test_llm_non_disponible_par_defaut():
    with patch("services.ia.llm_backend.urllib.request.urlopen", side_effect=ConnectionRefusedError):
        llm = LLMBackend()
        assert not llm.disponible()


def test_llm_disponible_avec_modele():
    response = _mock_response([{"name": "phi3"}])
    with patch("services.ia.llm_backend.urllib.request.urlopen", return_value=response):
        llm = LLMBackend()
        assert llm.disponible()


def test_llm_cache_disponibilite():
    with patch("services.ia.llm_backend.urllib.request.urlopen", side_effect=ConnectionRefusedError):
        llm = LLMBackend()
        assert not llm.disponible()
        assert not llm.disponible()


def test_llm_detecte_modele_prefere():
    response = _mock_response([{"name": "gemma:2b"}, {"name": "phi3"}])
    with patch("services.ia.llm_backend.urllib.request.urlopen", return_value=response):
        llm = LLMBackend()
        llm.disponible()
        assert llm.modele_effectif == "gemma:2b"


def test_llm_modele_specifie_priorite():
    response = _mock_response([{"name": "phi3"}, {"name": "gemma:2b"}])
    with patch("services.ia.llm_backend.urllib.request.urlopen", return_value=response):
        llm = LLMBackend(modele="phi3")
        assert llm.disponible()
        assert llm.modele_effectif == "phi3"


def test_get_backend_singleton():
    b1 = get_backend()
    b2 = get_backend()
    assert b1 is b2


def test_llm_refonte_naturel_texte_simple():
    """Si le LLM est indisponible, retourne le texte inchangé."""
    with patch.object(LLMBackend, "disponible", return_value=False):
        llm = LLMBackend()
        resultat = llm.reformuler_naturel("Bonjour")
        assert resultat == "Bonjour"


def test_llm_refonte_naturel_avec_llm():
    """Avec le LLM, reformule le texte en version naturelle."""
    with patch.object(LLMBackend, "disponible", return_value=True), \
         patch.object(LLMBackend, "_generer", return_value="Bonjour ! Comment allez-vous aujourd'hui ?"):
        llm = LLMBackend()
        resultat = llm.reformuler_naturel("Bonjour, allez vous bien ?")
        assert resultat == "Bonjour ! Comment allez-vous aujourd'hui ?"


def test_llm_detecter_intention_conviviale():
    with patch.object(LLMBackend, "disponible", return_value=True), \
         patch.object(LLMBackend, "_generer", return_value="conversation"):
        llm = LLMBackend()
        assert llm.detecter_intention("Bonjour, comment allez-vous ?") == "conversation"
