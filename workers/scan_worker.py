# workers/scan_worker.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.models import ScanResult
from core.scanner import FileScanner


class ScanWorker(QThread):
    """
    Фоновый поток: сканирует директорию проекта.

    Сигналы:
        scan_complete(ScanResult) — сканирование завершено успешно
        scan_error(str)           — произошла ошибка (сообщение для пользователя)
        status_update(str)        — промежуточный текст для статус-бара
    """

    scan_complete  = pyqtSignal(object)   # ScanResult
    scan_error     = pyqtSignal(str)
    status_update  = pyqtSignal(str)

    def __init__(self, root_path: Path, parent=None):
        super().__init__(parent)
        self._root_path = root_path
        self._scanner   = FileScanner()

    def run(self) -> None:
        """Выполняется в фоновом потоке."""
        try:
            self.status_update.emit(f"Сканирование: {self._root_path.name}...")
            result: ScanResult = self._scanner.scan(self._root_path)
            self.scan_complete.emit(result)

        except ValueError as e:
            # Путь не является директорией
            self.scan_error.emit(f"Ошибка: {e}")

        except Exception as e:
            # Любая непредвиденная ошибка
            self.scan_error.emit(
                f"Неожиданная ошибка при сканировании:\n{type(e).__name__}: {e}"
            )