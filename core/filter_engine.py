# core/filter_engine.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.models import FileNode, SkipReason, CheckState, Profile
from core.utils import normalize_extension


class FilterEngine:
    """
    Применяет 6-шаговую иерархию правил фильтрации из ТЗ (раздел 3.3).

    Порядок приоритетов (от наивысшего к низшему):
      1. Ручное снятие галочки в GUI          → безусловное исключение
      2. Белый список                          → безусловное включение*
      3. Чёрный список                         → исключить
      4. Игнорируемые расширения               → исключить
      5. Превышение лимита размера             → исключить
      6. Бинарный файл (null-байты)            → исключить

    * Файлы из белого списка всё равно исключаются, если они бинарные.
    """

    _BINARY_CHECK_BYTES = 8192   # Проверяем первые 8 КБ

    def __init__(self, profile: Profile):
        self._profile = profile

        # Предварительная нормализация для быстрого поиска O(1)
        self._whitelist_set: set[str] = {
            self._normalize(p) for p in profile.whitelist if p.strip()
        }
        self._blacklist_set: set[str] = {
            self._normalize(p) for p in profile.blacklist if p.strip()
        }
        self._ext_set: set[str] = {
            normalize_extension(e)
            for e in profile.ignored_extensions if e.strip()
        }
        self._max_bytes: int = max(1, int(profile.max_file_size_kb * 1024))

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def should_include(
        self, node: FileNode
    ) -> tuple[bool, Optional[SkipReason]]:
        """
        Определяет, включать ли файл в итоговую сборку.

        Returns:
            (True, None)              — включить
            (False, SkipReason.XXX)   — исключить с указанием причины
            (False, None)             — папка или снятый вручную узел
        """
        # Папки сами по себе не попадают в вывод
        if node.is_dir:
            return False, None

        # Шаг 1: Ручной выбор в GUI
        if node.check_state == CheckState.UNCHECKED:
            return False, SkipReason.UNCHECKED

        # Шаг 2: Белый список (обходит шаги 3–5, но НЕ шаг 6)
        if self._in_whitelist(node):
            if node.has_permission_error:
                return False, SkipReason.PERMISSION
            if self._is_binary(node.abs_path):
                return False, SkipReason.BINARY
            return True, None

        # Шаг 3: Чёрный список
        if self._in_blacklist(node):
            return False, SkipReason.BLACKLIST

        # Шаг 4: Фильтр расширений
        if node.extension in self._ext_set:
            return False, SkipReason.EXTENSION

        # Шаг 5: Лимит размера
        if node.size_bytes > self._max_bytes:
            return False, SkipReason.SIZE

        # Шаг 6: Проверка на бинарность (fallback-защита)
        if node.has_permission_error:
            return False, SkipReason.PERMISSION
        if self._is_binary(node.abs_path):
            return False, SkipReason.BINARY

        return True, None

    def mark_nodes(self, root: FileNode) -> None:
        """
        Проставляет флаги in_whitelist / in_blacklist на всём дереве.
        Используется GUI для подсветки.
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
        Исключение срабатывает, если:
        - Имя самого файла в чёрном списке, ИЛИ
        - Любой компонент пути (родительская папка) в чёрном списке.

        Это позволяет написать «node_modules» и исключить все файлы внутри.
        """
        if self._normalize(node.name) in self._blacklist_set:
            return True
        for part in node.rel_path.parts:
            if self._normalize(part) in self._blacklist_set:
                return True
        return False

    @staticmethod
    def _is_binary(path: Path) -> bool:
        """
        Эвристика бинарности: ищем null-байт (\x00) в первых 8 КБ.
        При любой ошибке доступа считаем файл НЕ бинарным —
        реальная ошибка будет поймана при чтении в генераторе.
        """
        try:
            with open(path, "rb") as f:
                return b"\x00" in f.read(FilterEngine._BINARY_CHECK_BYTES)
        except (OSError, PermissionError):
            return False

    @staticmethod
    def _normalize(s: str) -> str:
        """Нижний регистр + прямые слэши + без ведущих/ведомых слэшей."""
        return s.lower().replace("\\", "/").strip("/")

    def _mark_recursive(self, node: FileNode) -> None:
        if node.is_dir:
            node.in_blacklist = self._normalize(node.name) in self._blacklist_set
            node.in_whitelist = False
            for child in node.children:
                self._mark_recursive(child)
        else:
            node.in_whitelist = self._in_whitelist(node)
            node.in_blacklist = (
                not node.in_whitelist and self._in_blacklist(node)
            )