# workers/generate_worker.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.models import FileNode, Profile, GenerationResult
from core.filter_engine import FilterEngine
from core.generator import TextGenerator
from core.analytics import AnalyticsEngine


class GenerateWorker(QThread):
    """
    Фоновый поток: фильтрует файлы, генерирует текст, считает токены.

    Сигналы:
        generation_complete(GenerationResult, str) — готово; второй аргумент — уровень токенов
        generation_error(str)                      — ошибка
        status_update(str)                         — промежуточный текст

    Args:
        root_node:     Корневой FileNode из последнего ScanResult.
        profile:       Текущий профиль настроек.
        estimate_only: True — только оценить (не нужно сохранять), False — полная генерация.
    """

    generation_complete = pyqtSignal(object, str)   # (GenerationResult, token_level)
    generation_error    = pyqtSignal(str)
    status_update       = pyqtSignal(str)

    def __init__(
        self,
        root_node: FileNode,
        profile: Profile,
        estimate_only: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._root_node    = root_node
        self._profile      = profile
        self._estimate_only = estimate_only
        self._analytics    = AnalyticsEngine()

    def run(self) -> None:
        """Выполняется в фоновом потоке."""
        try:
            # Шаг 1: Фильтрация
            self.status_update.emit("Применяю фильтры...")
            engine = FilterEngine(self._profile)

            # Шаг 2: Генерация текста
            action = "Оцениваю" if self._estimate_only else "Генерирую"
            self.status_update.emit(f"{action} текст...")
            generator = TextGenerator()
            result: GenerationResult = generator.generate(
                self._root_node, self._profile, engine
            )

            # Шаг 3: Подсчёт токенов
            self.status_update.emit("Считаю токены...")
            self._analytics.enrich(result)
            token_level = self._analytics.get_token_level(result.token_count)

            self.generation_complete.emit(result, token_level)

        except Exception as e:
            self.generation_error.emit(
                f"Ошибка при генерации:\n{type(e).__name__}: {e}"
            )