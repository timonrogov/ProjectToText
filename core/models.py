# core/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto


# ---------------------------------------------------------------------------
# Перечисление состояния чекбокса (независимо от Qt, чтобы core не зависел от GUI)
# ---------------------------------------------------------------------------

class CheckState(Enum):
    UNCHECKED = auto()
    CHECKED = auto()
    PARTIALLY_CHECKED = auto()  # только для папок


# ---------------------------------------------------------------------------
# Узел дерева файловой системы
# ---------------------------------------------------------------------------

@dataclass
class FileNode:
    """Представляет один файл или папку в дереве проекта."""

    abs_path: Path                          # Абсолютный путь: /home/user/project/src/main.py
    rel_path: Path                          # Относительный от корня проекта: src/main.py
    is_dir: bool                            # True — папка, False — файл
    size_bytes: int = 0                     # Размер в байтах (0 для папок)
    extension: str = ""                     # Расширение в нижнем регистре: ".py", ".js"
    children: list[FileNode] = field(default_factory=list)  # Дочерние узлы (для папок)
    check_state: CheckState = CheckState.CHECKED

    # Метки списков (проставляются FilterEngine при обновлении настроек)
    in_whitelist: bool = False
    in_blacklist: bool = False
    has_permission_error: bool = False

    def __post_init__(self):
        # Нормализуем расширение: всегда нижний регистр
        if not self.is_dir:
            self.extension = self.abs_path.suffix.lower()

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024

    @property
    def name(self) -> str:
        return self.abs_path.name

    def __repr__(self) -> str:
        kind = "DIR" if self.is_dir else "FILE"
        return f"FileNode({kind}, {self.rel_path})"


# ---------------------------------------------------------------------------
# Результат сканирования
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    """Результат, возвращаемый FileScanner.scan()."""

    root: FileNode                  # Корневой узел (папка проекта)
    total_files: int = 0            # Суммарное количество файлов (рекурсивно)
    total_dirs: int = 0             # Суммарное количество папок
    scan_duration_ms: float = 0.0   # Время сканирования в миллисекундах


# ---------------------------------------------------------------------------
# Запись о пропущенном файле (для отчёта)
# ---------------------------------------------------------------------------

class SkipReason(str, Enum):
    """Причина пропуска файла. Используется как строка (str, Enum) для отображения в GUI."""
    UNCHECKED   = "Снят вручную"
    WHITELIST   = "Белый список"        # теоретически не используется как пропуск
    BLACKLIST   = "Черный список"
    EXTENSION   = "Расширение"
    SIZE        = "Превышение размера"
    BINARY      = "Бинарный файл"
    PERMISSION  = "Нет доступа"
    NOT_FOUND   = "Файл не найден"
    ENCODE_ERR  = "Ошибка кодировки"


@dataclass
class SkippedFile:
    """Запись о файле, не попавшем в итоговую сборку."""

    name: str           # Имя файла с расширением: "main.py"
    rel_path: str       # Относительный путь: "src/main.py"
    size_kb: float      # Размер в КБ
    reason: SkipReason  # Причина пропуска


# ---------------------------------------------------------------------------
# Результат генерации / оценки
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    """Результат, возвращаемый TextGenerator.generate()."""

    text: str                               # Итоговый сгенерированный текст
    included_files: int = 0                 # Количество включённых файлов
    total_files: int = 0                    # Всего файлов в дереве (с отмеченными)
    size_bytes: int = 0                     # Размер итогового текста в байтах
    token_count: int = 0                    # Заполняется AnalyticsEngine после генерации
    skipped_files: list[SkippedFile] = field(default_factory=list)

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_human(self) -> str:
        """Человекочитаемый размер: '1.23 MB' или '450.5 KB'."""
        if self.size_bytes >= 1024 * 1024:
            return f"{self.size_mb:.2f} MB"
        return f"{self.size_kb:.1f} KB"


# ---------------------------------------------------------------------------
# Профиль настроек (пресет)
# ---------------------------------------------------------------------------

class OutputFormat(str, Enum):
    PLAIN    = "plain"
    MARKDOWN = "markdown"
    XML      = "xml"


@dataclass
class Profile:
    """Полный набор настроек фильтрации и форматирования."""

    profile_name: str = "Default"
    version: str = "1.0"

    # Фильтры
    max_file_size_kb: int = 20
    whitelist: list[str] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=list)
    ignored_extensions: list[str] = field(default_factory=list)

    # Настройки вывода
    output_format: OutputFormat = OutputFormat.MARKDOWN
    remove_empty_lines: bool = False
    include_file_stats: bool = True

    def to_dict(self) -> dict:
        """Сериализация в словарь для сохранения в JSON."""
        return {
            "profile_name": self.profile_name,
            "version": self.version,
            "filters": {
                "max_file_size_kb": self.max_file_size_kb,
                "whitelist": self.whitelist,
                "blacklist": self.blacklist,
                "ignored_extensions": self.ignored_extensions,
            },
            "output_settings": {
                "format": self.output_format.value,
                "remove_empty_lines": self.remove_empty_lines,
                "include_file_stats": self.include_file_stats,
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        """Десериализация из словаря (загрузка из JSON)."""
        filters = d.get("filters", {})
        output  = d.get("output_settings", {})

        fmt_str = output.get("format", "markdown")
        try:
            fmt = OutputFormat(fmt_str)
        except ValueError:
            fmt = OutputFormat.MARKDOWN

        return cls(
            profile_name        = d.get("profile_name", "Unnamed"),
            version             = d.get("version", "1.0"),
            max_file_size_kb    = int(filters.get("max_file_size_kb", 20)),
            whitelist           = list(filters.get("whitelist", [])),
            blacklist           = list(filters.get("blacklist", [])),
            ignored_extensions  = [e.lower() for e in filters.get("ignored_extensions", [])],
            output_format       = fmt,
            remove_empty_lines  = bool(output.get("remove_empty_lines", False)),
            include_file_stats  = bool(output.get("include_file_stats", True)),
        )