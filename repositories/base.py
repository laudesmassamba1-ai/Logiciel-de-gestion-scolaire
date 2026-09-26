
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
        #
        # Les ids locaux sont reattribues vers les ids serveur par
        # api.mapping au moment de l'envoi (references par noms / uuid) :
        #   * « send »    -> envoyer maintenant (payload reattribue) ;
        #   * « skip »    -> la cible n'existe pas encore sur le serveur :
        #                    on garde l'ecriture locale ET on met en file pour
        #                    re-essayer au prochain drain (sinon perte silente) ;
        #   * « enqueue » -> resolution impossible maintenant : on met en
        #                    file, le drain reessaiera (vrai moyen de retry).
        server_sent = False
        # ECRITURE LOCALE D'ABORD : si elle echoue, l'envoi serveur ne doit
        # jamais avoir eu lieu (sinon un eleve reste orphelin cote serveur).
        # L'interface relit la base locale pour afficher, le drain s'occupe
        # de normaliser ulterieurement.
        result = fn(*args, **kwargs)
        if network.sync_active() and network.is_online():
            from api import mapping
            action = mapping.remap(method, endpoint, payload)
            if action[0] == "send":
                _, endpoint2, payload2 = action
                for _ in range(2):
                    try:
                        from api.client import _request
                        _, err = _request(method, endpoint2, json=payload2)
                    except Exception:
                        err = "echec reseau"
                    if not err:
                        server_sent = True
                        break
                else:
                    self._enqueue(method, endpoint, payload)
            elif action[0] == "enqueue":
                self._enqueue(method, endpoint, payload)
            elif action[0] == "done":
                # Operation insynchronisable (tarif annexe) : locale, ni
                # envoi ni file.
                pass
            elif action[0] == "skip":
                self._enqueue(method, endpoint, payload)
        elif network.sync_active() and not network.is_online():
            self._enqueue(method, endpoint, payload)
        return result
