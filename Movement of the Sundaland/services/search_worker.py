"""
services/search_worker.py
Background QThread for location search — prevents UI freeze during
Nominatim online queries (which can take up to 8 seconds).
"""

from PyQt6.QtCore import QThread, pyqtSignal
from services.location_search import search_location


class SearchWorker(QThread):
    """Run location search in background thread."""

    result_ready = pyqtSignal(str, list, str)   # query, results, source
    error        = pyqtSignal(str)
    finished     = pyqtSignal()

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self._query = query
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            results, source = search_location(self._query)
            if not self._abort:
                self.result_ready.emit(self._query, results, source)
        except Exception as e:
            if not self._abort:
                self.error.emit(str(e))
        finally:
            self.finished.emit()
