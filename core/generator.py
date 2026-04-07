# core/generator.py
from __future__ import annotations

import datetime
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

    Поддерживает форматы: plain, markdown, xml.
    Оптимизирован по памяти: части собираются в list, затем join().
    """

    def generate(
        self,
        root: FileNode,
        profile: Profile,
        filter_engine: FilterEngine,
    ) -> GenerationResult:
        """Основной метод генерации."""
        parts:   list[str]       = []
        skipped: list[SkippedFile] = []
        included_count = 0
        total_count    = 0

        for file_node in self._walk_files(root):
            total_count += 1
            include, reason = filter_engine.should_include(file_node)

            if not include:
                if reason and reason != SkipReason.UNCHECKED:
                    skipped.append(SkippedFile(
                        name     = file_node.name,
                        rel_path = str(file_node.rel_path),
                        size_kb  = file_node.size_kb,
                        reason   = reason,
                    ))
                continue

            content, read_error = self._read_file(file_node.abs_path)

            if read_error:
                skipped.append(SkippedFile(
                    name     = file_node.name,
                    rel_path = str(file_node.rel_path),
                    size_kb  = file_node.size_kb,
                    reason   = read_error,
                ))
                continue

            if profile.remove_empty_lines:
                content = self._strip_empty_lines(content)

            rel_path_str = str(file_node.rel_path).replace("\\", "/")
            block = self._format_block(
                rel_path = rel_path_str,
                content  = content,
                fmt      = profile.output_format,
                ext      = file_node.extension,
            )
            parts.append(block)
            included_count += 1

        # Опциональный блок статистики в начале файла
        header_parts: list[str] = []
        if profile.include_file_stats:
            header_parts.append(
                self._build_stats_header(
                    included_count  = included_count,
                    total_count     = total_count,
                    skipped_count   = len(skipped),
                    output_format   = profile.output_format,
                    project_name    = root.name,
                )
            )

        all_parts = header_parts + parts
        final_text = "\n\n".join(all_parts)

        return GenerationResult(
            text           = final_text,
            included_files = included_count,
            total_files    = total_count,
            size_bytes     = len(final_text.encode("utf-8")),
            skipped_files  = skipped,
        )

    # ------------------------------------------------------------------
    # Заголовок со статистикой
    # ------------------------------------------------------------------

    @staticmethod
    def _build_stats_header(
        included_count: int,
        total_count:    int,
        skipped_count:  int,
        output_format:  OutputFormat,
        project_name:   str,
    ) -> str:
        """
        Генерирует блок метаинформации для LLM в начале контекстного файла.
        Формат зависит от выбранного шаблона вывода.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"Project: {project_name}",
            f"Generated: {now}",
            f"Files included: {included_count} / {total_count}",
            f"Files skipped:  {skipped_count}",
        ]

        if output_format == OutputFormat.PLAIN:
            separator = "=" * 60
            return (
                f"{separator}\n"
                f"  LLM CONTEXT — {project_name.upper()}\n"
                f"{separator}\n"
                + "\n".join(lines)
                + f"\n{separator}"
            )

        elif output_format == OutputFormat.MARKDOWN:
            content = "\n".join(f"- **{line.split(':')[0]}:** {':'.join(line.split(':')[1:]).strip()}"
                                for line in lines)
            return f"## 📦 Context Info\n\n{content}"

        elif output_format == OutputFormat.XML:
            xml_lines = "\n".join(
                f"  <{key.strip().lower().replace(' ', '_')}>"
                f"{val.strip()}"
                f"</{key.strip().lower().replace(' ', '_')}>"
                for item in lines
                for key, *rest in [item.split(":", 1)]
                for val in rest
            )
            return f"<context_info>\n{xml_lines}\n</context_info>"

        return ""

    # ------------------------------------------------------------------
    # Форматирование блока файла
    # ------------------------------------------------------------------

    @staticmethod
    def _format_block(
        rel_path: str,
        content:  str,
        fmt:      OutputFormat,
        ext:      str,
    ) -> str:
        if fmt == OutputFormat.PLAIN:
            return (
                f"--- Файл: {rel_path} ---\n"
                f"{content}\n"
                f"--- Конец файла ---"
            )

        elif fmt == OutputFormat.MARKDOWN:
            lang = TextGenerator._get_md_lang(ext)
            return (
                f"### Файл: `{rel_path}`\n"
                f"```{lang}\n"
                f"{content}\n"
                f"```"
            )

        elif fmt == OutputFormat.XML:
            return (
                f'<file path="{rel_path}">\n'
                f"<![CDATA[\n"
                f"{content}\n"
                f"]]>\n"
                f"</file>"
            )

        return content

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _walk_files(root: FileNode) -> Generator[FileNode, None, None]:
        if root.is_dir:
            for child in root.children:
                yield from TextGenerator._walk_files(child)
        else:
            yield root

    @staticmethod
    def _read_file(path: Path) -> tuple[str, SkipReason | None]:
        """
        Читает файл с максимально устойчивой обработкой ошибок.
        errors='replace' гарантирует, что UnicodeDecodeError не прервёт сборку.
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), None
        except FileNotFoundError:
            # Файл исчез между сканированием и генерацией
            return "", SkipReason.NOT_FOUND
        except PermissionError:
            return "", SkipReason.PERMISSION
        except OSError:
            return "", SkipReason.ENCODE_ERR

    @staticmethod
    def _strip_empty_lines(text: str) -> str:
        return "\n".join(
            line for line in text.splitlines() if line.strip()
        )

    @staticmethod
    def _get_md_lang(extension: str) -> str:
        mapping = {
            ".py":    "python",   ".js":    "javascript",
            ".ts":    "typescript", ".jsx":  "jsx",
            ".tsx":   "tsx",      ".html":  "html",
            ".css":   "css",      ".scss":  "scss",
            ".less":  "less",     ".json":  "json",
            ".yaml":  "yaml",     ".yml":   "yaml",
            ".xml":   "xml",      ".md":    "markdown",
            ".sh":    "bash",     ".bash":  "bash",
            ".zsh":   "bash",     ".ps1":   "powershell",
            ".sql":   "sql",      ".rs":    "rust",
            ".go":    "go",       ".java":  "java",
            ".kt":    "kotlin",   ".cs":    "csharp",
            ".cpp":   "cpp",      ".c":     "c",
            ".h":     "c",        ".hpp":   "cpp",
            ".rb":    "ruby",     ".php":   "php",
            ".swift": "swift",    ".r":     "r",
            ".lua":   "lua",      ".dart":  "dart",
            ".toml":  "toml",     ".ini":   "ini",
            ".cfg":   "ini",      ".env":   "bash",
        }
        return mapping.get(extension.lower(), "")