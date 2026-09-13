
import json

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
        """Boucle de synchro : le sommeil est decoupe en pas de 0,5 s pour
        que requestInterruption() soit pris en compte rapidement (sinon un
        sleep de 15 s retarderait l'arret bien au-dela du wait(3 s))."""
        pas = 0.5
        restant = self._interval
        while not self.isInterruptionRequested():
            if api_disponible(force=True):
                network.set_online()
                self.status_changed.emit("online")
                self._pull_structure()
                self._drain_queue()
            else:
                network.set_offline()
                self.status_changed.emit("offline")
                restant = self._interval
            while restant > 0 and not self.isInterruptionRequested():
                self.msleep(int(pas * 1000))
                restant -= pas
            restant = self._interval


    def _pull_structure(self):
        import time as _time
        now = _time.monotonic()
        if now - self._last_pull < self.PULL_INTERVAL:
            return
        try:
            from services.sync_service import pull_structure, pull_donnees, pull_comptes
            self._last_pull = now
            pull_structure()
            pull_donnees()
            pull_comptes()
        except Exception as exc:
            self.sync_error.emit(f"Erreur de synchro : {exc}")


    def _drain_queue(self):
        try:
            rows = db.dequeue_pending()
        except Exception:
            # Base temporairement verrouillee (pull en cours) : on passera
            # au prochain cycle au lieu de tuer le thread de synchro.
            return
        sent = 0
        for row in rows:
            try:
                payload = json.loads(row["payload"])
                method, endpoint = row["method"], row["endpoint"]
                from api import mapping
                action = mapping.remap(method, endpoint, payload)
                if action[0] in ("skip", "enqueue"):
                    # « skip » : la reference n'existe pas sur le serveur
                    # (l'ecriture locale est legitime, rien a y envoyer).
                    # « enqueue » : resolution toujours impossible (reseaux
                    # coupe) — inutile de rejouer a l'infini, on archive.
                    db.mark_queue_done(row["id"])
                    continue
                if action[0] == "send":
                    endpoint, payload = action[1], action[2]
                uuid_client = row["uuid_client"] if row["uuid_client"] else payload.get("uuid_client")
                if uuid_client and method == "POST" and endpoint == "/eleve":
                    payload = {"uuid_client": uuid_client, "eleve": payload}
                _, err = _request(method, endpoint, json=payload)
            except Exception:
                err = "echec envoi"
            if err:
                db.mark_queue_failed(row["id"])
            else:
                db.mark_queue_done(row["id"])
                sent += 1
        if sent:
            self.sync_done.emit(sent)
