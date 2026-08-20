

from core.config import SYNC_ACTIVE as _cfg_sync

_state = "offline"


def sync_active():
    return _cfg_sync


def is_online():
    return _cfg_sync and _state == "online"


def set_online():
    global _state
    _state = "online"


def set_offline():
    global _state
    _state = "offline"
