"""Identite et presence de CE poste sur le reseau de l'ecole.

Chaque poste porte un identifiant stable (fichier `data/poste.json`) et
s'annonce regulierement au serveur (`POST /present`, via le worker de
synchronisation). Le serveur devient la source de verite de « qui est
connecte » : la page Reseau des postes s'appuie dessus.
"""

import json
import platform
import uuid

from core.config import APP_VERSION, data_dir, est_hote


def uuid_poste():
    """Identifiant stable de cette machine (cree une seule fois)."""
    dossier = data_dir()
    fichier = dossier / "poste.json"
    try:
        if fichier.exists():
            info = json.loads(fichier.read_text(encoding="utf-8"))
            if info.get("uuid_poste"):
                return str(info["uuid_poste"])
    except (OSError, ValueError):
        pass
    nouvel = str(uuid.uuid4())
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        fichier.write_text(
            json.dumps({"uuid_poste": nouvel},
                       ensure_ascii=False, indent=1),
            encoding="utf-8")
    except OSError:
        pass
    return nouvel


def identite_poste():
    """Fiche de presence envoyee au serveur a chaque battement de coeur."""
    import socket
    return {
        "uuid_poste": uuid_poste(),
        "nom_poste": str(socket.gethostname())[:120],
        "adresse_ip": "",
        "systeme": platform.platform()[:80],
        "version_app": APP_VERSION,
        "est_hote": est_hote(),
    }


def annoncer_presence():
    """Battement de coeur vers le serveur. Renvoie None si c'est passe,
    sinon le message d'erreur (le serveur est injoignable)."""
    from api.client import _request
    _, err = _request("POST", "/present", json=identite_poste())
    return err