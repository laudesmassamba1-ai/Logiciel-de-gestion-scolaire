import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _html_ddg():
    return ('<html><div class="result">'
            '<a class="result__a" href="//duckduckgo.com/l/?uddg='
            'https%3A%2F%2Ffr.wikipedia.org%2Fwiki%2FOgoou%C3%A9'
            '&rut=abc">Ogoou&eacute; &mdash; Wikipedia</a>'
            '<a class="result__snippet">Ce fleuve coule au Gabon.</a>'
            '<a class="result__a" href="https://www.geo.fr/fleuves">'
            'GEO Fleuves</a>'
            '<a class="result__snippet">Le plus long fleuve du Gabon.</a>'
            '</div></html>')


class TestNettoyage:
    def test_nettoyer_supprime_balises(self):
        from services.ia.webrecherche import _nettoyer
        assert _nettoyer("<a>x</a>&eacute;&mdash;") == "x é—"
        assert _nettoyer(None) == ""

    def test_nettoyer_url_uddg(self):
        from services.ia.webrecherche import _nettoyer_url
        url = _nettoyer_url(
            "//duckduckgo.com/l/?uddg=https%3A%2F%2Fex.org%2Fa%3Fb%3D1&rut=z")
        assert url == "https://ex.org/a?b=1"
        assert _nettoyer_url("https://direct.org/x") == "https://direct.org/x"


class TestFormater:
    def test_format_et_troncature(self):
        from services.ia import webrecherche
        long = "x" * 300
        res = [webrecherche.Resultat("Titre", "https://u.fr/1", long)]
        texte = webrecherche.formater(res)
        assert "1. Titre" in texte
        assert "https://u.fr/1" in texte
        assert "..." in texte
        assert webrecherche.formater([]) == ""


class TestRecherche:
    def test_duckduckgo_parse(self, monkeypatch):
        from services.ia import webrecherche
        def fake_fetch(url, timeout=None):
            if "html.duckduckgo.com" in url:
                return _html_ddg()
            return "<html></html>"
        monkeypatch.setattr(webrecherche, "_fetch", fake_fetch)
        web = webrecherche.RechercheWeb()
        web._ok = None
        res = web.rechercher("fleuve du gabon", nombre=5)
        assert len(res) == 2
        assert res[0].titre.startswith("Ogooué")
        assert "fr.wikipedia.org/wiki/Ogooué" in res[0].url
        assert "Gabon" in res[0].extrait
        assert "GEO Fleuves" in res[1].titre

    def test_repli_wikipedia(self, monkeypatch):
        from services.ia import webrecherche
        def fake_fetch(url, timeout=None):
            if "html.duckduckgo.com" in url:
                return None
            if "fr.wikipedia.org/w/api.php" in url:
                return ('{"query":{"search":['
                        '{"title":"Ogooué","snippet":"<b>fleuve</b> du Gabon"}'
                        ']}}')
            return None
        monkeypatch.setattr(webrecherche, "_fetch", fake_fetch)
        monkeypatch.setattr(webrecherche.RechercheWeb, "disponible",
                            lambda self: True)
        web = webrecherche.RechercheWeb()
        web._ok = None
        res = web.rechercher("fleuve du gabon", nombre=3)
        assert len(res) == 1
        assert res[0].titre == "Ogooué"
        assert "fr.wikipedia.org/wiki/Ogoou%C3%A9" in res[0].url

    def test_hors_ligne_retourne_vide(self, monkeypatch):
        from services.ia import webrecherche
        monkeypatch.setattr(webrecherche, "_fetch", lambda url, timeout=None: None)
        web = webrecherche.RechercheWeb()
        web._ok = None
        assert not web.disponible()
        assert web.rechercher("capitale du congo") == []

    def test_depassement_timeout_ne_leve_jamais(self, monkeypatch):
        from services.ia import webrecherche
        def fake_urlopen(req, timeout=None):
            raise OSError("connection refused")
        monkeypatch.setattr(webrecherche.urllib.request, "urlopen",
                            fake_urlopen)
        web = webrecherche.RechercheWeb()
        web._ok = None
        assert web.rechercher("meteo de libreville") == []

    def test_cache_disponibilite(self, monkeypatch):
        from services.ia import webrecherche
        compteur = {"n": 0}
        def fake_fetch(url, timeout=None):
            compteur["n"] += 1
            if "html.duckduckgo.com" in url:
                return _html_ddg()
            return None
        monkeypatch.setattr(webrecherche, "_fetch", fake_fetch)
        web = webrecherche.RechercheWeb()
        web._ok = None
        assert web.disponible()
        assert web.disponible()
        assert compteur["n"] == 1