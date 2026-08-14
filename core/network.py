


SYNC_ACTIVE = False

_state = "offline"



def sync_active():
    return SYNC_ACTIVE



def is_online():
    return SYNC_ACTIVE and _state == "online"



def set_online():
    global _state
    _state = "online"



def set_offline():
    global _state
    _state = "offline"
