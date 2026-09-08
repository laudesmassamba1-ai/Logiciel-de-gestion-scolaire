

from core.config import SYNC_ACTIVE as _cfg_sync

_state = "offline"
_sync_active = None


def sync_active():
    # Bascule runtime (assistant graphique) prioritaire sur la config.
    # NOTE : si sync.json est modifie MANUELLEMENT pendant l'execution,
    # la valeur runtime n'est pas relue (choix assume : la config ne
    # change que via l'assistant, qui appelle set_sync_active).
    return _cfg_sync if _sync_active is None else _sync_active


def set_sync_active(valeur):
    global _sync_active
    _sync_active = bool(valeur)


def is_online():
    return sync_active() and _state == "online"


def set_online():
    global _state
    _state = "online"


def set_offline():
    global _state
    _state = "offline"
