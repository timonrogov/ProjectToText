# core/generator.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from core.models import (
    FileNode, Profile, GenerationResult,
    SkippedFile, SkipReason, OutputFormat, CheckState,
)
from core.filter_engine import FilterEngine


class TextGenerator:
    """
    Обходит дерево FileNode, применяет FilterEngine к каждому файлу
    и склеивает содержимое в единый текстовый массив.

    Поддерживает три формата: plain, markdown, xml.
    Оптимизирован по памяти: строки собираются в list, затем join().
    """

    def generate(
        self,
        root: FileNode,
        profile: Profile,
        filter_engine: FilterEngine,
    ) -> GenerationResult:
        """
        Основной метод генерации.

        Args:
            root:          Корневой узел дерева (результат сканирования).
            profile:       Текущий профиль настроек.
            filter_engine: Проинициализированный движок фильтрации.

        Returns:
            GenerationResult с итоговым текстом и статистикой.
        """
        parts: list[str] = []       # Сюда накапливаем блоки текста
        skipped: list[SkippedFile] = []
        included_count = 0
        total_count = 0

        # Рекурсивно обходим всё дерево
        for file_node in self._walk_files(root):
            total_count += 1

            include, reason = filter_engine.should_include(file_node)

            if not include:
                # Не пишем в журнал файлы, снятые вручную (CheckState.UNCHECKED)
                if reason != SkipReason.UNCHECKED:
                    skipped.append(SkippedFile(
                        name     = file_node.name,
                        rel_path = str(file_node.rel_path),
                        size_kb  = file_node.size_kb,
                        reason   = reason,
                    ))
                continue

            # Файл прошёл фильтрацию — читаем и форматируем
            content, read_error = self._read_file(file_node.abs_path)

            if read_error:
                skipped.append(SkippedFile(
                    name     = file_node.name,
                    rel_path = str(file_node.rel_path),
                    size_kb  = file_node.size_kb,
                    reason   = read_error,
                ))
                continue

            # Опция минификации
            if profile.remove_empty_lines:
                content = self._strip_empty_lines(content)

            # Форматируем блок по выбранному шаблону
            block = self._format_block(
                rel_path = str(file_node.rel_path).replace("\\", "/"),
                content  = content,
                fmt      = profile.output_format,
                ext      = file_node.extension,
            )
            parts.append(block)
            included_count += 1

        # Собираем итоговый текст (эффективнее, чем +=)
        final_text = "\n\n".join(parts)
        final_bytes = final_text.encode("utf-8")

        return GenerationResult(
            text           = final_text,
            included_files = included_count,
            total_files    = total_count,
            size_bytes     = len(final_bytes),
            token_count    = 0,     # Заполнит AnalyticsEngine
            skipped_files  = skipped,
        )

    # ------------------------------------------------------------------
    # Форматирование блока файла
    # ------------------------------------------------------------------

    def _format_block(
        self,
        rel_path: str,
        content: str,
        fmt: OutputFormat,
        ext: str,
    ) -> str:
        """Оборачивает содержимое файла в нужный шаблон."""

        if fmt == OutputFormat.PLAIN:
            return (
                f"--- Файл: {rel_path} ---\n"
                f"{content}\n"
                f"--- Конец файла ---"
            )

        elif fmt == OutputFormat.MARKDOWN:
            # Определяем язык для подсветки синтаксиса в блоке кода
            lang = self._get_md_lang(ext)
            return (
                f"### Файл: `{rel_path}`\n"
                f"```{lang}\n"
                f"{content}\n"
                f"```"
            )

        elif fmt == OutputFormat.XML:
            # CDATA позволяет не экранировать спецсимволы внутри блока
            return (
                f'<file path="{rel_path}">\n'
                f"<![CDATA[\n"
                f"{content}\n"
                f"]]>\n"
                f"</file>"
            )

        # Fallback
        return content

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _walk_files(root: FileNode) -> Generator[FileNode, None, None]:
        """Генератор: обходит дерево и yield-ит только файловые узлы."""
        if root.is_dir:
            for child in root.children:
                yield from TextGenerator._walk_files(child)
        else:
            yield root

    @staticmethod
    def _read_file(path: Path) -> tuple[str, SkipReason | None]:
        """
        Читает файл с корректной обработкой ошибок.

        Returns:
            (content, None)              — успешно прочитан
            ("", SkipReason.NOT_FOUND)   — файл исчез после сканирования
            ("", SkipReason.PERMISSION)  — нет прав
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), None
        except FileNotFoundError:
            return "", SkipReason.NOT_FOUND
        except PermissionError:
            return "", SkipReason.PERMISSION
        except OSError:
            return "", SkipReason.ENCODE_ERR

    @staticmethod
    def _strip_empty_lines(text: str) -> str:
        """Убирает строки, состоящие только из пробелов/табуляций."""
        return "\n".join(
            line for line in text.splitlines()
            if line.strip()
        )

    @staticmethod
    def _get_md_lang(extension: str) -> str:
        """
        Возвращает идентификатор языка для markdown-блока кода.
        Например: ".py" → "python", ".js" → "javascript".
        """
        mapping = {
            ".py":    "python",
            ".js":    "javascript",
            ".ts":    "typescript",
            ".jsx":   "jsx",
            ".tsx":   "tsx",
            ".html":  "html",
            ".css":   "css",
            ".scss":  "scss",
            ".less":  "less",
            ".json":  "json",
            ".yaml":  "yaml",
            ".yml":   "yaml",
            ".xml":   "xml",
            ".md":    "markdown",
            ".sh":    "bash",
            ".bash":  "bash",
            ".zsh":   "bash",
            ".ps1":   "powershell",
            ".sql":   "sql",
            ".rs":    "rust",
            ".go":    "go",
            ".java":  "java",
            ".kt":    "kotlin",
            ".cs":    "csharp",
            ".cpp":   "cpp",
            ".c":     "c",
            ".h":     "c",
            ".hpp":   "cpp",
            ".rb":    "ruby",
            ".php":   "php",
            ".swift": "swift",
            ".r":     "r",
            ".lua":   "lua",
            ".dart":  "dart",
            ".toml":  "toml",
            ".ini":   "ini",
            ".cfg":   "ini",
            ".env":   "bash",
            ".dockerfile": "dockerfile",
        }
        return mapping.get(extension.lower(), "")