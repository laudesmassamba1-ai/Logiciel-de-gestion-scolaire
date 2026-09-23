"""Connexion automatique d'un poste au serveur de l'ecole.

Objectif : ne rien avoir a configurer. Des qu'un poste est sur le meme
reseau que le PC hote (WiFi de l'ecole, Ethernet, ou meme une connexion
Internet vers un serveur distant), il rejoint le serveur tout seul et se
synchronise.

Regles de securite :
  - un poste configure comme HOTE (serveur_auto dans sync.json) ne
    cherche jamais un autre serveur : il reste la source de verite ;
  - une connexion distante (nom de domaine public) n'est jamais remplacee
    par un serveur local decouvert : on respecte le choix de l'ecole ;
  - l'utilisateur peut refuser : `auto_connect=False` (case decochee dans
    l'assistant) desactive la recherche automatique.
"""

import ipaddress
from urllib.parse import urlparse


def _url_locale(url):
    """Vrai si l'URL pointe vers la machine locale ou le reseau prive
    (donc susceptible d'etre remplacee par un serveur decouvert)."""
    if not url:
        return True
    hote = urlparse(url if "://" in url else f"http://{url}").hostname or ""
    if hote in ("127.0.0.1", "localhost", "0.0.0.0", ""):
        return True
    try:
        return ipaddress.ip_address(hote).is_private
    except ValueError:
        # Nom de domaine public -> connexion Internet voulue, on garde.
        return False


def auto_connect_active():
    from core.config import lire_config_sync
    return bool(lire_config_sync().get("auto_connect", True))


def code_ecole_local():
    from core.config import code_ecole
    return code_ecole()


def nouveau_code_ecole():
    """Code court et lisible identifiant une ecole (ex. « 9F3A2C7D »)."""
    import secrets
    return "GSE-" + secrets.token_hex(3).upper()


def definir_code_ecole(code):
    """Enregistre le code de l'ecole de ce poste (majuscules)."""
    from core.config import ecrire_config_sync
    code = (code or "").strip().upper()
    ecrire_config_sync(code_ecole=code)
    return code


def code_ecole_du_serveur(url, timeout=2.0):
    """Interroge un serveur pour connaitre le code de SON ecole.

    Renvoie le code, ou None si le serveur ne repond pas / n'expose pas
    l'information (ancien serveur)."""
    try:
        import httpx
        rep = httpx.get(url.rstrip("/") + "/ecole", timeout=timeout)
        if rep.status_code >= 400:
            return None
        return str((rep.json() or {}).get("code_ecole", "") or "").strip()
    except Exception:
        return None


def doit_auto_connecter():
    """Indique si CE poste doit chercher un serveur de l'ecole."""
    from core.config import API_BASE_URL, lire_config_sync
    cfg = lire_config_sync()
    if cfg.get("serveur_auto"):
        return False
    if not cfg.get("auto_connect", True):
        return False
    return _url_locale(API_BASE_URL)


def connecter_a(url, persister=True, code=None):
    """Bascule ce poste en mode client connecte au serveur `url`.

    `code` : code de l'ecole a enregistrer (adopte au premier rattachement).
    S'il est fourni et non vide, il devient le code de ce poste."""
    from core import config, network

    url = (url or "").rstrip("/")
    if not url:
        return None
    code = (code or "").strip().upper()
    if persister:
        from core.config import ecrire_config_sync
        valeurs = {"api_url": url, "sync_active": True,
                   "serveur_auto": False, "auto_connect": True, "pid": None}
        if code:
            valeurs["code_ecole"] = code
        ecrire_config_sync(**valeurs)
    # Mise a jour en memoire : les appels HTTP partent immediatement vers
    # la nouvelle adresse (api.client lit config.API_BASE_URL a chaque appel).
    config.API_BASE_URL = url
    network.set_sync_active(True)
    network.set_online()
    return url


def deconnecter(persister=True):
    """Repasse ce poste en mode autonome (ne cherche plus de serveur)."""
    from core import network

    if persister:
        from core.config import ecrire_config_sync
        ecrire_config_sync(sync_active=False, serveur_auto=False,
                           auto_connect=False, pid=None)
    network.set_sync_active(False)
    network.set_offline()


def chercher_et_connecter(duree=4.0, timeout=2.0):
    """Decouvre un serveur de LA MEME ecole sur le reseau et s'y connecte.

    Renvoie l'URL retenue, ou None. Un poste sans code d'ecole connu ne
    s'auto-connecte jamais : le premier rattachement est explicite (via
    l'assistant) afin qu'une ecole ne rejoigne jamais une autre."""
    if not doit_auto_connecter():
        return None
    code = code_ecole_local()
    if not code:
        return None
    from services import discovery
    trouve = discovery.trouver_et_tester_serveur(
        duree=duree, timeout=timeout, code_attendu=code)
    if not trouve:
        return None
    url, code_serveur = trouve
    if code_serveur and code_serveur != code:
        return None
    return connecter_a(url, code=code)
