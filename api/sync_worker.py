
import json
import threading

from PyQt5.QtCore import QThread, pyqtSignal

from api.client import _request, api_disponible
from core import network
from database import db

# Synchronise les acces a la file : le worker tourne en arriere-plan et la
# commande manuelle « Synchroniser maintenant » peut lancer un vidage en meme
# temps — sans verrou, les deux enverraient les MEMES lignes (double envoi).
_VERROU_DRAIN = threading.Lock()


def vider_file_attente(interruption=None) -> int:
    """Pousse la file d'attente locale vers le serveur (thread-safe).

    Renvoie le nombre de lignes effectivement envoyees. Ligne par ligne :
      * « skip »    -> cible pas encore sur le serveur : la ligne est
        GARDEE dans la file et re-jouee au cycle suivant, des que la cible
        existe (jamais de perte silencieuse) ;
      * « enqueue » -> resolution interrompue (coupure reseau) : rejouee ;
      * erreur      -> tentative+1, rejouee jusqu'a TENTATIVE_MAX ;
      * succes      -> retiree de la file."""
    with _VERROU_DRAIN:
        try:
            rows = db.dequeue_pending()
        except Exception:
            return 0
        sent = 0
        for row in rows:
            if interruption and interruption():
                break
            try:
                payload = json.loads(row["payload"])
                method, endpoint = row["method"], row["endpoint"]
                from api import mapping
                action = mapping.remap(method, endpoint, payload)
                if action[0] == "skip":
                    continue
                if action[0] == "enqueue":
                    # La resolution a echoue (coupure reseau pendant les
                    # requetes) : on rejoue au cycle suivant (jamais de
                    # perte silencieuse).
                    db.mark_queue_failed(row["id"])
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
        return sent


class SyncWorker(QThread):

    status_changed = pyqtSignal(str)
    sync_done = pyqtSignal(int)
    sync_error = pyqtSignal(str)

    # Le serveur est la source de verite pour la structure de l'ecole :
    # on la rapatrie au plus toutes les PULL_INTERVAL secondes quand on
    # est en ligne, pour que les modifications du directeur se propagent.
    PULL_INTERVAL = 60

    # Poste client hors ligne : on cherche le serveur de l'ecole sur le
    # reseau au plus toutes les DISCOVERY_INTERVAL secondes. Des qu'il est
    # joignable (meme WiFi, Ethernet ou Internet), on s'y connecte seul.
    DISCOVERY_INTERVAL = 15

    def __init__(self, interval=15):
        super().__init__()
        self._interval = interval
        self._last_pull = 0.0
        self._last_discover = 0.0


    def run(self):
        """Boucle de synchro : le sommeil est decoupe en pas de 0,5 s pour
        que requestInterruption() soit pris en compte rapidement (sinon un
        sleep de 15 s retarderait l'arret bien au-dela du wait(3 s))."""
        pas = 0.5
        restant = self._interval
        while not self.isInterruptionRequested():
            if api_disponible(force=True):
                network.set_online()
                from services.poste import annoncer_presence
                annoncer_presence()
                self.status_changed.emit("online")
                self._pull_structure()
                self._drain_queue()
            else:
                network.set_offline()
                self.status_changed.emit("offline")
                self._tenter_autoconnexion()
                restant = self._interval
            while restant > 0 and not self.isInterruptionRequested():
                self.msleep(int(pas * 1000))
                restant -= pas
            restant = self._interval


    def _tenter_autoconnexion(self):
        """Rejoint automatiquement le serveur de l'ecole decouvert sur le
        reseau. Sans effet si ce poste est l'hote, si l'utilisateur a
        decoche la connexion automatique, ou si une adresse Internet a ete
        configuree volontairement."""
        import time as _time
        now = _time.monotonic()
        if now - self._last_discover < self.DISCOVERY_INTERVAL:
            return
        self._last_discover = now
        try:
            from services import connexion
            url = connexion.chercher_et_connecter(duree=3.0)
            if url:
                self.status_changed.emit("online")
        except Exception:
            pass


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
        sent = vider_file_attente(interruption=self.isInterruptionRequested)
        if sent:
            self.sync_done.emit(sent)
