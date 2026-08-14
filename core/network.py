# etat du reseau : vrai quand le serveur est accessible, sinon mode local

# passe a True quand le serveur FastAPI sera deployee
SYNC_ACTIVE = False

_state = "offline"


# dit si la synchronisation est activee dans cette installation
def sync_active():
    return SYNC_ACTIVE


# dit si le serveur est actuellement joignable
def is_online():
    return SYNC_ACTIVE and _state == "online"


# marque le serveur comme joignable (appele par le sync_worker)
def set_online():
    global _state
    _state = "online"


# marque le serveur comme hors ligne (appele par le sync_worker)
def set_offline():
    global _state
    _state = "offline"
