import threading

from core.config import SYNC_ACTIVE as _cfg_sync

_state = "offline"
_sync_active = None
_VERROU = threading.Lock()


def sync_active():
    with _VERROU:
        return _cfg_sync if _sync_active is None else _sync_active


def set_sync_active(valeur):
    global _sync_active
    with _VERROU:
        _sync_active = bool(valeur)


def is_online():
    with _VERROU:
        return (_cfg_sync if _sync_active is None else _sync_active) and _state == "online"


def set_online():
    global _state
    with _VERROU:
        _state = "online"


def set_offline():
    global _state
    with _VERROU:
        _state = "offline"