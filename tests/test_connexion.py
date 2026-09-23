"""Tests de la connexion automatique au serveur de l'ecole (cloisonnement).

Couvre `services/connexion.py` (regles de decision, bascule client, code
d'ecole), `services/discovery.py` (filtrage par code) et l'integration cote
`SyncWorker` (recherche periodique).
"""
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Regles d'adresse ──────────────────────────────────────────────────
class TestUrlLocale:
    @pytest.mark.parametrize("url", [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://192.168.1.5:8000",
        "http://10.0.0.2:8000",
        "http://172.16.0.9:8000",
        "",
    ])
    def test_adresses_locales(self, url):
        from services import connexion
        assert connexion._url_locale(url) is True

    @pytest.mark.parametrize("url", [
        "https://ecole.example.com",
        "http://monserveur.ddns.net:8000",
        "https://gestion.ecole.ci",
    ])
    def test_adresses_publiques(self, url):
        from services import connexion
        assert connexion._url_locale(url) is False


# ── Decision : ce poste doit-il chercher un serveur ? ─────────────────
class TestDoitAutoConnecter:
    def _cfg(self, monkeypatch, cfg, api_url="http://127.0.0.1:8000"):
        import core.config as config
        monkeypatch.setattr(config, "lire_config_sync", lambda: cfg)
        monkeypatch.setattr(config, "API_BASE_URL", api_url)

    def test_defaut_actif_sur_poste_autonome(self, monkeypatch):
        from services import connexion
        self._cfg(monkeypatch, {})
        assert connexion.doit_auto_connecter() is True

    def test_hote_avec_serveur_auto_ne_cherche_pas(self, monkeypatch):
        from services import connexion
        self._cfg(monkeypatch, {"serveur_auto": True})
        assert connexion.doit_auto_connecter() is False

    def test_utilisateur_a_desactive(self, monkeypatch):
        from services import connexion
        self._cfg(monkeypatch, {"auto_connect": False})
        assert connexion.doit_auto_connecter() is False

    def test_connexion_internet_conservee(self, monkeypatch):
        from services import connexion
        self._cfg(monkeypatch, {}, api_url="https://ecole.example.com")
        assert connexion.doit_auto_connecter() is False


# ── Code de l'ecole ───────────────────────────────────────────────────
class TestCodeEcole:
    def test_nouveau_code_format(self):
        from services import connexion
        code = connexion.nouveau_code_ecole()
        assert code.startswith("GSE-")
        assert len(code) >= 9

    def test_definir_code_enregistre(self, monkeypatch):
        import core.config as config
        from services import connexion
        ecrits = {}
        monkeypatch.setattr(config, "ecrire_config_sync",
                            lambda **kw: ecrits.update(kw))
        assert connexion.definir_code_ecole(" gse-abc123 ") == "GSE-ABC123"
        assert ecrits.get("code_ecole") == "GSE-ABC123"

    def test_code_du_serveur(self, monkeypatch):
        from services import connexion
        class Rep:
            status_code = 200
            def json(self):
                return {"code_ecole": "GSE-88AA"}
        import httpx
        monkeypatch.setattr(httpx, "get", lambda *a, **k: Rep())
        assert connexion.code_ecole_du_serveur("http://10.0.0.8:8000") == "GSE-88AA"

    def test_code_du_serveur_injoignable(self, monkeypatch):
        from services import connexion
        class Rep:
            status_code = 403
        import httpx
        monkeypatch.setattr(httpx, "get", lambda *a, **k: Rep())
        assert connexion.code_ecole_du_serveur("http://10.0.0.8:8000") is None

    def test_code_du_serveur_sans_entete(self, monkeypatch):
        from services import connexion
        import httpx
        def _boom(*a, **k):
            raise httpx.ConnectError("x")
        monkeypatch.setattr(httpx, "get", _boom)
        assert connexion.code_ecole_du_serveur("http://10.0.0.8:8000") is None


# ── Bascule client / autonome ─────────────────────────────────────────
class TestBascule:
    def test_connecter_a_met_a_jour_etat(self, monkeypatch):
        import core.config as config
        import core.network as network
        from services import connexion

        ecrits = {}
        monkeypatch.setattr(
            config, "ecrire_config_sync",
            lambda **kw: ecrits.update(kw))
        actifs = []
        monkeypatch.setattr(network, "set_sync_active",
                            lambda v: actifs.append(v))
        monkeypatch.setattr(network, "set_online", lambda: actifs.append("online"))

        url = connexion.connecter_a("http://192.168.0.10:8000/", code="GSE-X")

        assert url == "http://192.168.0.10:8000"
        assert config.API_BASE_URL == "http://192.168.0.10:8000"
        assert ecrits.get("api_url") == "http://192.168.0.10:8000"
        assert ecrits.get("sync_active") is True
        assert ecrits.get("auto_connect") is True
        assert ecrits.get("code_ecole") == "GSE-X"
        assert True in actifs and "online" in actifs

    def test_deconnecter_repasse_en_autonome(self, monkeypatch):
        import core.config as config
        import core.network as network
        from services import connexion

        ecrits = {}
        monkeypatch.setattr(
            config, "ecrire_config_sync",
            lambda **kw: ecrits.update(kw))
        desactives = []
        monkeypatch.setattr(network, "set_sync_active",
                            lambda v: desactives.append(v))
        monkeypatch.setattr(network, "set_offline", lambda: desactives.append("off"))

        connexion.deconnecter()

        assert ecrits.get("sync_active") is False
        assert ecrits.get("auto_connect") is False
        assert False in desactives and "off" in desactives

    def test_connecter_a_vide_ne_fait_rien(self, monkeypatch):
        import core.config as config
        from services import connexion
        monkeypatch.setattr(
            config, "ecrire_config_sync",
            lambda **kw: pytest.fail("ne doit rien persister"))
        assert connexion.connecter_a("") is None


# ── Recherche + connexion (cloisonnement) ─────────────────────────────
class TestChercherEtConnecter:
    def _preparer(self, monkeypatch, code_local, trouve):
        from services import connexion, discovery
        monkeypatch.setattr(connexion, "doit_auto_connecter", lambda: True)
        monkeypatch.setattr(connexion, "code_ecole_local", lambda: code_local)
        monkeypatch.setattr(
            discovery, "trouver_et_tester_serveur",
            lambda duree=4.0, timeout=2.0, code_attendu=None: trouve)
        return connexion

    def test_connecte_si_serveur_de_la_meme_ecole(self, monkeypatch):
        import core.config as config
        import core.network as network
        from services import connexion

        monkeypatch.setattr(config, "ecrire_config_sync",
                            lambda **kw: None)
        monkeypatch.setattr(network, "set_sync_active", lambda v: None)
        monkeypatch.setattr(network, "set_online", lambda: None)

        connexion = self._preparer(
            monkeypatch, "GSE-MEME",
            ("http://192.168.0.5:8000", "GSE-MEME"))
        url = connexion.chercher_et_connecter()
        assert url == "http://192.168.0.5:8000"
        assert config.API_BASE_URL == "http://192.168.0.5:8000"

    def test_poste_sans_code_ne_s_auto_connecte_jamais(self, monkeypatch):
        """Un poste qui n'a jamais ete rattache (aucun code) ne s'auto-
        connecte pas : le premier rattachement est toujours explicite."""
        from services import connexion, discovery
        connexion = self._preparer(monkeypatch, "", "http://x")
        assert connexion.chercher_et_connecter() is None

    def test_ecole_differente_refusee(self, monkeypatch):
        import core.config as config
        from services import connexion
        monkeypatch.setattr(config, "ecrire_config_sync",
                            lambda **kw: pytest.fail("ne doit pas ecrire"))
        connexion = self._preparer(
            monkeypatch, "GSE-A",
            ("http://192.168.0.99:8000", "GSE-B"))
        assert connexion.chercher_et_connecter() is None

    def test_renvoie_none_sans_serveur(self, monkeypatch):
        from services import connexion
        connexion = self._preparer(monkeypatch, "GSE-A", None)
        assert connexion.chercher_et_connecter() is None

    def test_ne_cherche_pas_si_interdit(self, monkeypatch):
        from services import connexion, discovery
        monkeypatch.setattr(connexion, "doit_auto_connecter", lambda: False)
        monkeypatch.setattr(
            discovery, "trouver_et_tester_serveur",
            lambda duree=4.0, timeout=2.0, code_attendu=None:
                pytest.fail("ne doit pas chercher"))
        monkeypatch.setattr(connexion, "code_ecole_local", lambda: "GSE-A")
        monkeypatch.setattr(connexion, "connecter_a",
                            lambda url, code=None: pytest.fail("pas de connexion"))
        assert connexion.chercher_et_connecter() is None


# ── Filtrage par code dans la decouverte ──────────────────────────────
class TestDiscoveryCloisonnement:
    def test_accepte_le_code_correspondant(self, monkeypatch):
        from services import discovery
        monkeypatch.setattr(
            discovery, "trouver_serveur",
            lambda duree=5.0: [{"ip": "10.0.0.5", "port": 8000,
                                "ecole": "GSE-AAA"}])
        monkeypatch.setattr(discovery, "serveur_joignable",
                            lambda url, timeout=2.0: "GSE-AAA")
        assert discovery.trouver_et_tester_serveur(
            duree=0.1, code_attendu="GSE-AAA") == \
            ("http://10.0.0.5:8000", "GSE-AAA")

    def test_ignore_une_autre_ecole(self, monkeypatch):
        from services import discovery
        monkeypatch.setattr(
            discovery, "trouver_serveur",
            lambda duree=5.0: [{"ip": "10.0.0.5", "port": 8000,
                                "ecole": "GSE-BBB"}])
        monkeypatch.setattr(discovery, "serveur_joignable",
                            lambda url, timeout=2.0: "GSE-BBB")
        assert discovery.trouver_et_tester_serveur(
            duree=0.1, code_attendu="GSE-AAA") is None

    def test_accepte_serveur_sans_annonce_mais_avec_code_http(self, monkeypatch):
        """Ancien serveur ne diffusant pas le code, mais qui y repond en HTTP."""
        from services import discovery
        monkeypatch.setattr(
            discovery, "trouver_serveur",
            lambda duree=5.0: [{"ip": "10.0.0.5", "port": 8000, "ecole": ""}])
        monkeypatch.setattr(discovery, "serveur_joignable",
                            lambda url, timeout=2.0: "GSE-AAA")
        assert discovery.trouver_et_tester_serveur(
            duree=0.1, code_attendu="GSE-AAA") == \
            ("http://10.0.0.5:8000", "GSE-AAA")


# ── Integration SyncWorker ────────────────────────────────────────────
class TestSyncWorkerAutoConnexion:
    def test_tente_la_connexion_et_respecte_intervalle(self, monkeypatch):
        from api.sync_worker import SyncWorker
        from services import connexion

        appels = []
        monkeypatch.setattr(
            connexion, "chercher_et_connecter",
            lambda duree=3.0: appels.append(duree) or "http://10.0.0.2:8000")

        worker = SyncWorker()
        # Premier appel : recherche autorisee.
        worker._last_discover = 0.0
        worker._tenter_autoconnexion()
        assert len(appels) == 1

        # Appel immediat : bloque par l'intervalle (pas de scan a chaque boucle).
        worker._tenter_autoconnexion()
        assert len(appels) == 1

        # Apres l'intervalle, la recherche repart.
        worker._last_discover = time.monotonic() - SyncWorker.DISCOVERY_INTERVAL - 1
        worker._tenter_autoconnexion()
        assert len(appels) == 2