# base des depots : aiguille les ecritures entre le serveur et le local
import json
import uuid

from core import network
from database import db


# cree une reference unique (par exemple REC-XXXX ou DEP-XXXX)
def _gen_reference(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class RepositoryBase:
    # place une operation hors ligne dans la file d'attente de synchronisation
    def _enqueue(self, method, endpoint, payload):
        db.enqueue(method=method, endpoint=endpoint,
                   payload=json.dumps(payload, ensure_ascii=False, default=str))

    # aiguillage d'une ecriture : serveur si en ligne, sinon local + file
    def _route_write(self, method, endpoint, payload, fn, *args, **kwargs):
        if network.sync_active() and network.is_online():
            # TODO (serveur en ligne) : appeler api.client, puis verifier la reponse
            pass
        result = fn(*args, **kwargs)
        if network.sync_active() and not network.is_online():
            self._enqueue(method, endpoint, payload)
        return result
