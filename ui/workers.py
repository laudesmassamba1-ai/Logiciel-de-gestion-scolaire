
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal


_live_tasks = set()


class _TaskSignals(QObject):
    done = pyqtSignal(object)


class _Task(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _TaskSignals()

    def run(self):
        try:
            result = self.fn()
        except Exception as exc:
            result = exc
        try:
            self.signals.done.emit(result)
        except RuntimeError:
            # Le recepteur (fenetre/page) a ete detruit entre-temps.
            pass


def run_async(fn, on_done):
    task = _Task(fn)
    _live_tasks.add(task)

    def _handle(result):
        try:
            on_done(result)
        except RuntimeError:
            pass
        finally:
            _live_tasks.discard(task)

    task.signals.done.connect(_handle)
    QThreadPool.globalInstance().start(task)
    return task
