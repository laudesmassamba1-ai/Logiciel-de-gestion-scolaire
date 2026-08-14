
import time

from PyQt5.QtCore import QThread, pyqtSignal

from api import client
from core import network
from database import db


class SyncWorker(QThread):

    status_changed = pyqtSignal(str)
    sync_done = pyqtSignal(int)
    sync_error = pyqtSignal(str)

    def __init__(self, interval=15):
        super().__init__()
        self._interval = interval


    def run(self):
        while not self.isInterruptionRequested():
            if client.api_disponible(force=True):
                network.set_online()
                self.status_changed.emit("online")
                self._drain_queue()
            else:
                network.set_offline()
                self.status_changed.emit("offline")
            time.sleep(self._interval)


    def _drain_queue(self):
        rows = db.dequeue_pending()
        for row in rows:


            pass
