# core/filter_engine.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.models import FileNode, SkipReason, CheckState, Profile


class FilterEngine:
    """
    Применяет 6-шаговую иерархию правил фильтрации из ТЗ (раздел 3.3).

    Принимает профиль настроек при инициализации.
    Метод should_include() — главная точка входа.
    """

    # Максимальное количество байт для проверки бинарности (8 КБ достаточно)
    _BINARY_CHECK_BYTES = 8192

    def __init__(self, profile: Profile):
        self._profile = profile

        # Предварительно нормализуем списки для быстрого поиска
        self._whitelist_set: set[str] = {
            self._normalize(p) for p in profile.whitelist
        }
        self._blacklist_set: set[str] = {
            self._normalize(p) for p in profile.blacklist
        }
        self._ext_set: set[str] = {
            e.lower() if e.startswith(".") else f".{e.lower()}"
            for e in profile.ignored_extensions
        }
        self._max_bytes: int = int(profile.max_file_size_kb * 1024)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def should_include(
        self, node: FileNode
    ) -> tuple[bool, Optional[SkipReason]]:
        """
        Определяет, нужно ли включать файл в итоговую сборку.

        Returns:
            (True, None)              — включить файл
            (False, SkipReason.XXX)   — исключить с указанием причины
        """
        # Папки сами по себе не попадают в вывод — только их файлы
        if node.is_dir:
            return False, None

        # --- Шаг 1: Ручной выбор в GUI ---
        if node.check_state == CheckState.UNCHECKED:
            return False, SkipReason.UNCHECKED

        # --- Шаг 2: Белый список (наивысший приоритет) ---
        if self._in_whitelist(node):
            # Белый список обходит ВСЕ остальные проверки,
            # кроме одной: бинарный файл всё равно не читаем
            if self._is_binary(node.abs_path):
                return False, SkipReason.BINARY
            return True, None

        # --- Шаг 3: Чёрный список ---
        if self._in_blacklist(node):
            return False, SkipReason.BLACKLIST

        # --- Шаг 4: Фильтр расширений ---
        if node.extension in self._ext_set:
            return False, SkipReason.EXTENSION

        # --- Шаг 5: Лимит размера ---
        if node.size_bytes > self._max_bytes:
            return False, SkipReason.SIZE

        # --- Шаг 6: Проверка на бинарность (fallback-защита) ---
        if self._is_binary(node.abs_path):
            return False, SkipReason.BINARY

        return True, None

    def mark_nodes(self, root: FileNode) -> None:
        """
        Проходит по всему дереву и проставляет флаги
        in_whitelist / in_blacklist на каждом узле.
        Используется для подсветки в GUI.
        """
        self._mark_recursive(root)

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _in_whitelist(self, node: FileNode) -> bool:
        name     = self._normalize(node.name)
        rel_path = self._normalize(str(node.rel_path))
        return name in self._whitelist_set or rel_path in self._whitelist_set

    def _in_blacklist(self, node: FileNode) -> bool:
        """
        Проверяем и само имя файла, и имена ВСЕХ его родительских директорий.
        Это позволяет исключить node_modules/lodash/index.js, просто указав
        'node_modules' в чёрном списке.
        """
        # Проверяем имя самого файла
        if self._normalize(node.name) in self._blacklist_set:
            return True

        # Проверяем каждый компонент относительного пути
        for part in node.rel_path.parts:
            if self._normalize(part) in self._blacklist_set:
                return True

        return False

    @staticmethod
    def _is_binary(path: Path) -> bool:
        """
        Эвристика: файл считается бинарным, если в первых 8 КБ
        содержится нулевой байт (\x00).
        """
        try:
            with open(path, "rb") as f:
                chunk = f.read(FilterEngine._BINARY_CHECK_BYTES)
                return b"\x00" in chunk
        except OSError:
            # Нет доступа или файл исчез — считаем не бинарным,
            # ошибку поймаем при реальном чтении в генераторе
            return False

    @staticmethod
    def _normalize(s: str) -> str:
        """Нормализация для сравнения: нижний регистр, прямые слэши."""
        return s.lower().replace("\\", "/").strip("/")

    def _mark_recursive(self, node: FileNode) -> None:
        if not node.is_dir:
            node.in_whitelist = self._in_whitelist(node)
            node.in_blacklist = self._in_blacklist(node)
        else:
            # Папка в чёрном списке — помечаем её саму
            node.in_blacklist = self._normalize(node.name) in self._blacklist_set
            for child in node.children:
                self._mark_recursive(child)