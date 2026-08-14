
import json
import uuid

from core import network
from database import db



def _gen_reference(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class RepositoryBase:

    def _enqueue(self, method, endpoint, payload):
        db.enqueue(method=method, endpoint=endpoint,
                   payload=json.dumps(payload, ensure_ascii=False, default=str))


    def _route_write(self, method, endpoint, payload, fn, *args, **kwargs):
        if network.sync_active() and network.is_online():

            pass
        result = fn(*args, **kwargs)
        if network.sync_active() and not network.is_online():
            self._enqueue(method, endpoint, payload)
        return result
