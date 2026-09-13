"""Point d'acces WiFi de l'ecole cree par le PC serveur.

Le poste hote transforme sa carte WiFi en hotspot afin que les autres
postes se connectent au reseau local, sans box ni Internet necessaire.

Internet EN MÊME TEMPS : quand le PC hote possede une autre source de
connexion (cable Ethernet vers le modem/box, telephone en USB, carte 4G),
le hotspot est cree en mode « partage » (ipv4.shared) : NetworkManager
fait du NAT et les postes connectes au hotspot recoivent l'Internet du
PC hote (creant une etiquette "ige"...) tout en synchronisant en local.

Composant requis : NetworkManager (nmcli). Dependance systeme, pas Python.
"""

import re
import shutil
import subprocess
import time

SSID_DEF = "Gestion-Ecole"
MOT_DE_PASSE_DEF = "Gestion2026"

_NOM_CONNEXION = "gs-hotspot"


class HotspotError(Exception):
    """Erreur lisible lors de la creation du point d'acces."""


def _nmcli(*args, timeout=25):
    """Exécute nmcli de maniere sure. Retourne le CompletedProcess ou un
    objet simulé avec returncode/etderr si nmcli manque ou se bloque."""
    if not nmcli_disponible():
        class _Absent:
            returncode = 127
            stdout = ""
            stderr = "NetworkManager (nmcli) n'est pas disponible sur ce poste."
        return _Absent()
    try:
        return subprocess.run(
            ["nmcli", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        class _Bloque:
            returncode = 124
            stdout = ""
            stderr = f"nmcli bloque (delai > {timeout}s)"
        return _Bloque()
    except OSError as exc:
        class _Erreur:
            returncode = 127
            stdout = ""
            stderr = f"Impossible de lancer nmcli : {exc}"
        return _Erreur()


def nmcli_disponible():
    return shutil.which("nmcli") is not None


def interface_wifi_visible():
    """Renvoie le nom de la premiere carte WiFi geree par NetworkManager."""
    rep = _nmcli("-t", "-f", "DEVICE,TYPE,STATE", "device", "status")
    for ligne in rep.stdout.splitlines():
        parts = ligne.split(":")
        if len(parts) >= 3 and parts[1] == "wifi":
            return parts[0]
    return None


def source_internet_disponible():
    """Detecte une source Internet sur le PC hote AUTRE que la carte WiFi
    (Ethernet câble vers la box, telephone/modem USB, carte 4G).

    Si c'est le cas, le hotspot cree en mode « shared » partagera
    automatiquement cet Internet aux postes connectes au reseau WiFi
    de l'ecole : Internet et synchro fonctionnent en MEME TEMPS.

    Renvoie le nom de l'interface source, ou None."""
    try:
        rep = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    for ligne in rep.stdout.splitlines():
        if "dev " not in ligne:
            continue
        # extraction de l'interface apres 'dev'
        _parts = ligne.split()
        try:
            idx = _parts.index("dev")
            dev = _parts[idx + 1] if idx + 1 < len(_parts) else None
        except ValueError:
            dev = None
        if not dev:
            continue
        # Sources Internet alternatives a la carte WiFi du hotspot :
        # Ethernet filaire, tethering USB (usb/enp), carte 4G (wwan).
        if (dev.startswith(("en", "eth", "usb", "wwan", "enp", "ens"))
                and "wl" not in dev):
            return dev
    return None


def reseau_deja_cree():
    """Indique si le hotspot est actif (present dans les connexions)."""
    rep = _nmcli("-t", "connection", "show")
    return any(l.startswith(_NOM_CONNEXION + ":") for l in rep.stdout.splitlines())


def hotspot_actif():
    return reseau_deja_cree()


def creer_hotspot(ssid=None, nom=None):
    """Cree et active le point d'acces WiFi de l'ecole.

    Renvoie le dict {ssid, mot_de_passe, partage, interface}.
    Leve HotspotError si le hotspot ne peut pas demarrer.
    """
    if not nmcli_disponible():
        raise HotspotError(
            "NetworkManager (nmcli) n'est pas installe sur ce poste "
            "hote. Utilisez un PC sous Linux (ou la panneau WiFi de "
            "Windows) pour creer le point d'acces.")

    iface = interface_wifi_visible()
    if not iface:
        raise HotspotError(
            "Aucune carte WiFi trouvee sur ce poste. Branchez une carte "
            "ou une cle WiFi pour creer le reseau de l'ecole.")

    ssid = (ssid or SSID_DEF).strip().replace(" ", "-")

    # Nettoyage d'une connexion precedente pour reconstructure.
    arreter_hotspot()

    # 1) Activer la carte (necessaire avant AP)
    _nmcli("-t", "radio", "wifi", "on")

    # 2) Creer le point d'acces en mode partage -> NAT automatique
    rep = _nmcli("connection", "add", "type", "wifi",
                 "con-name", _NOM_CONNEXION,
                 "ssid", ssid,
                 "mode", "ap",
                 "wifi-sec.key-mgmt", "wpa-psk",
                 "wifi-sec.psk", MOT_DE_PASSE_DEF,
                 "ipv4.method", "shared",
                 "ipv6.method", "shared",
                 "802-11-wireless.mode", "ap")
    if rep.returncode != 0:
        raise HotspotError(
            "Impossible de creer le point d'acces :\n" + rep.stderr.strip())

    # 3) Demarrer
    rep = _nmcli("connection", "up", _NOM_CONNEXION)
    if rep.returncode != 0:
        raise HotspotError(
            "Impossible d'activer le point d'acces :\n" + rep.stderr.strip())

    # 4) Verifier que l'AP a bien une adresse
    for _ in range(10):
        if _ip_ap(iface) is not None:
            break
        time.sleep(0.5)

    partage = source_internet_disponible()
    return {
        "ssid": ssid,
        "mot_de_passe": MOT_DE_PASSE_DEF,
        "partage": bool(partage),
        "source_internet": partage,
        "interface": iface,
    }


def _ip_ap(iface):
    rep = _nmcli("-t", "-f", "IP4.ADDRESS", "device", "show", iface)
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", rep.stdout)
    return m.group(1) if m else None


def adresse_passerelle():
    """Adresse IP du point d'acces (a saisir sur les postes clients)."""
    iface = interface_wifi_visible()
    if not iface:
        return None
    return _ip_ap(iface)


def arreter_hotspot():
    """Reste la connexion AP creee par creer_hotspot()."""
    if hotspot_actif():
        _nmcli("connection", "delete", _NOM_CONNEXION)
        # Laisser la carte reprendre ses connexions WiFi precedentes.
        _nmcli("-t", "radio", "wifi", "on")