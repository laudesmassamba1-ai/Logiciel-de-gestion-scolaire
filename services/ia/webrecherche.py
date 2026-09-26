"""Recherche web pour Charo — sans clé API, 100 % stdlib.

Charo peut utiliser Internet comme une source d'information supplémentaire
pour les questions qui ne relèvent pas des données scolaires (géographie,
actualité, culture générale...). Trois garanties :

1. Zéro clé / zéro compte : DuckDuckGo HTML par défaut, Wikipédia en repli.
2. Zéro blocage : chaque requête est bornée (timeout court), et la sonde
   « disponible » est mise en cache 30 s. Sans réseau, la recherche est
   simplement désactivée : Charo retombe sur son moteur local
   (mémoire, LLM optionnel via ollama, apprentissage) — l'application
   reste pleinement autonome et hors ligne.
3. Zéro ressource PC : tout est servi côté serveurs distants ; le poste
   ne fait qu'un GET et du parse de texte.

Usage :
    from services.ia import webrecherche
    web = webrecherche.get_recherche_web()
    if web.disponible():
        resultats = web.rechercher("capitale du Congo", nombre=5)
        print(webrecherche.formater(resultats, "capitale du Congo"))
"""

import html as _html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

_DDG_URL = "https://html.duckduckgo.com/html/"
_WIKI_URL = "https://fr.wikipedia.org/w/api.php"
_UA = "Mozilla/5.0 (X11; Linux x86_64) GestionScolaire/1.6"
_TIMEOUT = 6.0
_SONDE_TIMEOUT = 4.0
_CACHE_DISPO = 30.0
_MAX_RESULTATS = 5
_EXTRAIT_MAX = 180

_REG_TITRE = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
    re.S | re.I)
_REG_SNIPPET = re.compile(
    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.S | re.I)


class Resultat:
    """Un resultat de recherche web, sans aucune dependance GUI."""
    __slots__ = ("titre", "url", "extrait")

    def __init__(self, titre, url, extrait=""):
        self.titre = titre
        self.url = url
        self.extrait = extrait

    def __repr__(self):
        return f"<Resultat {self.titre!r} {self.url!r}>"


def _nettoyer(html_fragment):
    """Supprime les balises et decode les entites HTML."""
    texte = re.sub(r"<[^>]+>", " ", html_fragment or "")
    texte = _html.unescape(texte)
    return " ".join(texte.split())


def _nettoyer_url(href):
    """Les liens DuckDuckGo passent par /l/?uddg=... : on extrait la cible."""
    if not href:
        return ""
    if "uddg=" in href:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        if query.get("uddg"):
            return query["uddg"][0]
    if href.startswith("//"):
        href = "https:" + href
    return href


def _fetch(url, timeout=_TIMEOUT):
    """GET simple et sur. Retourne le corps texte ou None (aucune
    exception ne doit remonter jusqu'au moteur Charo)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            if getattr(rep, "status", 200) >= 400:
                return None
            corps = rep.read().decode("utf-8", errors="replace")
            return corps if corps else None
    except (urllib.error.URLError, urllib.error.HTTPError,
            OSError, ValueError):
        return None


def _rechercher_duckduckgo(question, nombre):
    """DuckDuckGo HTML : resultats titre / url / extrait."""
    url = _DDG_URL + "?" + urllib.parse.urlencode({"q": question})
    corps = _fetch(url, timeout=_TIMEOUT)
    if not corps:
        return []
    titres = list(_REG_TITRE.finditer(corps))
    snippets = list(_REG_SNIPPET.finditer(corps))
    resultats = []
    for i, m in enumerate(titres):
        if i >= nombre:
            break
        titre = _nettoyer(m.group(2))
        url_res = _nettoyer_url(m.group(1))
        extrait = _nettoyer(snippets[i].group(1)) if i < len(snippets) else ""
        if titre and url_res:
            resultats.append(Resultat(titre, url_res, extrait))
    return resultats


def _rechercher_wikipedia(question, nombre):
    """Repli fiable : recherche Wikipedia (JSON), sans compte."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": question,
        "format": "json",
        "srlimit": min(nombre, 10),
    }
    url = _WIKI_URL + "?" + urllib.parse.urlencode(params)
    corps = _fetch(url, timeout=_TIMEOUT)
    if not corps:
        return []
    try:
        donnees = json.loads(corps)
    except ValueError:
        return []
    resultats = []
    for s in donnees.get("query", {}).get("search", [])[:nombre]:
        titre = _nettoyer(s.get("title") or "")
        extrait = _nettoyer(s.get("snippet") or "")
        page = urllib.parse.quote_plus(titre.replace(" ", "_"))
        if titre:
            resultats.append(Resultat(
                titre, f"https://fr.wikipedia.org/wiki/{page}", extrait))
    return resultats


class RechercheWeb:
    """Point d'entree de la recherche web, avec sonde de disponibilite."""

    def __init__(self):
        self._ok = None
        self._teste_a = 0.0

    def disponible(self) -> bool:
        """True si Internet repond (sonde courte, cache 30 s)."""
        if self._ok is None or time.monotonic() - self._teste_a > _CACHE_DISPO:
            provisoire = _fetch(_DDG_URL, timeout=_SONDE_TIMEOUT) is not None
            self._ok = provisoire
            self._teste_a = time.monotonic()
        return self._ok

    def rechercher(self, question, nombre=_MAX_RESULTATS):
        """Recherche web : DuckDuckGo puis Wikipedia en repli.

        Retourne une liste de Resultat (vide si hors ligne ou sans
        resultats). Ne lève jamais."""
        if not question or not question.strip():
            return []
        if not self.disponible():
            return []
        try:
            resultats = _rechercher_duckduckgo(question, nombre)
            if not resultats:
                resultats = _rechercher_wikipedia(question, nombre)
            return resultats
        except Exception:
            return []


# ----------------------------------------------------------------------
# Mise en forme pour Charo
# ----------------------------------------------------------------------

def formater(resultats, question="", nombre=None):
    """Transforme les resultats en texte lisible pour le chat."""
    if not resultats:
        return ""
    lignes = []
    limite = nombre or len(resultats)
    for i, r in enumerate(resultats[:limite], start=1):
        extrait = r.extrait or ""
        if len(extrait) > _EXTRAIT_MAX:
            extrait = extrait[:_EXTRAIT_MAX - 3] + "..."
        lignes.append(f"{i}. {r.titre}")
        if extrait:
            lignes.append(f"   {extrait}")
        lignes.append(f"   Source : {r.url}")
    return "\n".join(lignes)


# Instance singleton (lazy)
_backend = None


def get_recherche_web():
    global _backend
    if _backend is None:
        _backend = RechercheWeb()
    return _backend