
import json
import uuid

from core import network
from database import db


def _gen_reference(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class RepositoryBase:

    def _enqueue(self, method, endpoint, payload):
        uuid_client = payload.get("uuid_client") if isinstance(payload, dict) else None
        db.enqueue(method=method, endpoint=endpoint,
                   payload=json.dumps(payload, ensure_ascii=False, default=str),
                   uuid_client=uuid_client)


    def _route_write(self, method, endpoint, payload, fn, *args, **kwargs):
        # Architecture « local-first » assume : l'ecriture locale a toujours
        # lieu (l'interface relit la base locale pour afficher), et le serveur
        # recoit la meme operation. Aucun doublon n'en resulte : le pull et
        # les routes serveur dedupliquent par uuid_client / cles naturelles.
        if network.sync_active() and network.is_online():
            # 1 retry immediat : resilience aux micro-coupures reseau
            # avant de basculer l'operation dans la file d'attente.
            for _ in range(2):
                try:
                    from api.client import _request
                    _, err = _request(method, endpoint, json=payload)
                except Exception:
                    err = "echec reseau"
                if not err:
                    break
            else:
                self._enqueue(method, endpoint, payload)
        result = fn(*args, **kwargs)
        if network.sync_active() and not network.is_online():
            self._enqueue(method, endpoint, payload)
        return result
