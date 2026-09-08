
import json
import time

from PyQt5.QtCore import QThread, pyqtSignal

from api.client import _request, api_disponible
from core import network
from database import db


class SyncWorker(QThread):

    status_changed = pyqtSignal(str)
    sync_done = pyqtSignal(int)
    sync_error = pyqtSignal(str)

    # Le serveur est la source de verite pour la structure de l'ecole :
    # on la rapatrie au plus toutes les PULL_INTERVAL secondes quand on
    # est en ligne, pour que les modifications du directeur se propagent.
    PULL_INTERVAL = 60

    def __init__(self, interval=15):
        super().__init__()
        self._interval = interval
        self._last_pull = 0.0


    def run(self):
        while not self.isInterruptionRequested():
            if api_disponible(force=True):
                network.set_online()
                self.status_changed.emit("online")
                self._pull_structure()
                self._drain_queue()
            else:
                network.set_offline()
                self.status_changed.emit("offline")
            time.sleep(self._interval)


    def _pull_structure(self):
        import time as _time
        now = _time.monotonic()
        if now - self._last_pull < self.PULL_INTERVAL:
            return
        try:
            from services.sync_service import pull_structure
            self._last_pull = now
            pull_structure()
        except Exception:
            pass  # jamais bloquant : le poste reste utilisable hors-ligne


    def _drain_queue(self):
        rows = db.dequeue_pending()
        sent = 0
        for row in rows:
            try:
                payload = json.loads(row["payload"])
                uuid_client = row["uuid_client"] if row["uuid_client"] else payload.get("uuid_client")
                if uuid_client and "/eleve" in row["endpoint"]:
                    payload = {"uuid_client": uuid_client, "eleve": payload}
                _, err = _request(row["method"], row["endpoint"], json=payload)
            except Exception:
                err = "echec envoi"
            if err:
                db.mark_queue_failed(row["id"])
            else:
                db.mark_queue_done(row["id"])
                sent += 1
        if sent:
            self.sync_done.emit(sent)
