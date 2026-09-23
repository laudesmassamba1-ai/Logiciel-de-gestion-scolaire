"""Decouverte automatique du serveur de l'ecole sur le reseau local.

Le poste serveur (hote) annonce sa presence par broadcast UDP ; les postes
clients ecoutent et affichent l'adresse sans avoir a la saisir a la main.
Cela couvre l'ensemble d'un etablissement (bâtiment / cour) tant que les
postes sont sur le meme reseau IP.

Protocole : datagramme UDP JSON {"gestion_scolaire": 1, "port": <int>}
envoye sur 255.255.255.255:<PORT>. Simple, sans dependance externe.
"""

import json
import socket
import threading
import time

PORT = 42300
MAGIC = "gestion_scolaire"
_TTL_ANNONCE = 4.0   # secondes entre chaque annonce du serveur
_DELAI_ECOUTE = 2.0  # secondes sans message avant de considrer la perte


class AnnonceurServeur(threading.Thread):
    """Cote hote : diffuse en boucle l'adresse du serveur sur le LAN.

    Arreter en appelant stop() et join().
    """

    def __init__(self, port_api, ip=None, interface=None, code_ecole=None):
        super().__init__(daemon=True, name="gs-annonceur")
        self._port_api = port_api
        self._ip = ip
        self._interface = interface or "0.0.0.0"
        self._code_ecole = (code_ecole or "").strip()
        self._arret = threading.Event()

    def stop(self):
        self._arret.set()

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError:
                pass
        except OSError:
            return
        while not self._arret.is_set():
            try:
                payload = json.dumps({"gestion_scolaire": 1,
                                      "port": self._port_api,
                                      "ecole": self._code_ecole})
                s.sendto(payload.encode("utf-8"), ("255.255.255.255", PORT))
            except OSError:
                pass
            self._arret.wait(_TTL_ANNONCE)
        s.close()


class DecouvreurServeur(threading.Thread):
    """Cote client : ecoute les annonces et remonte les adresses trouvees."""

    def __init__(self, port_ecoute=None):
        super().__init__(daemon=True, name="gs-decouvreur")
        self._port = port_ecoute or PORT
        self._arret = threading.Event()
        self._found = []

    def stop(self):
        self._arret.set()

    def obtenir(self):
        return list(self._found)

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", self._port))
            s.settimeout(0.5)
        except OSError:
            return
        while not self._arret.is_set():
            try:
                donnee, adr = s.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(donnee.decode("utf-8"))
                if msg.get(MAGIC) == 1 and msg.get("port"):
                    ip = adr[0]
                    ligne = {"ip": ip, "port": int(msg["port"]),
                             "ecole": str(msg.get("ecole", "") or "").strip()}
                    if ligne not in self._found:
                        self._found.append(ligne)
            except (ValueError, UnicodeDecodeError):
                continue
        s.close()


def trouver_serveur(duree=5.0):
    """Ecoute le reseau jusqu'a `duree` secondes et renvoie
    [{"ip": ..., "port": ...}] pour chaque serveur qui repond.

    Retour anticipe : des qu'un serveur est entendu, on rend la main sans
    attendre la fin du delai (important pour la connexion automatique au
    demarrage : rejoindre l'ecole en moins d'une seconde au lieu de 5)."""
    decouvreur = DecouvreurServeur()
    decouvreur.start()
    fin = time.monotonic() + duree
    try:
        while time.monotonic() < fin:
            if decouvreur.obtenir():
                break
            time.sleep(0.2)
    finally:
        decouvreur.stop()
        decouvreur.join(1.0)
    return decouvreur.obtenir()


def serveur_joignable(url, timeout=2.0):
    """Teste qu'un serveur GS repond a cette adresse.

    Renvoie None si injoignable, sinon le code d'ecole annonce par le
    serveur (chaine vide si le serveur n'en expose pas)."""
    try:
        import httpx
        rep = httpx.get(url.rstrip("/") + "/ecole", timeout=timeout)
        if rep.status_code >= 500:
            return None
        try:
            return str((rep.json() or {}).get("code_ecole", "") or "").strip()
        except ValueError:
            return ""
    except Exception:
        return None


def trouver_et_tester_serveur(duree=4.0, timeout=2.0, code_attendu=None):
    """Decouvre le premier serveur de l'ecole JOIGNABLE.

    Si `code_attendu` est fourni, seuls les serveurs qui annoncent/renvoient
    ce code sont retenus : c'est ce qui empeche une ecole de se connecter a
    une autre. En l'absence de code, aucun serveur n'est accepte (le premier
    rattachement doit etre explicite).

    Renvoie (url, code_ecole) ou None."""
    code_attendu = (code_attendu or "").strip()
    for res in trouver_serveur(duree):
        annonce = (res.get("ecole") or "").strip()
        if code_attendu and annonce and annonce != code_attendu:
            continue
        url = f"http://{res['ip']}:{res['port']}"
        code = serveur_joignable(url, timeout=timeout)
        if code is None:
            continue
        code = code or annonce
        if code_attendu and code != code_attendu:
            continue
        if not code_attendu and not code:
            continue
        return url, code
    return None