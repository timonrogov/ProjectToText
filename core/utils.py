# core/utils.py
from __future__ import annotations

from pathlib import Path


def format_size(size_bytes: int) -> str:
    """
    Конвертирует размер в байтах в человекочитаемую строку.

    Examples:
        500       → "500 B"
        10_240    → "10.0 KB"
        1_572_864 → "1.5 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    return f"{size_bytes / (1024 ** 3):.2f} GB"


def safe_relative_path(abs_path: Path, root: Path) -> Path:
    """
    Возвращает относительный путь от root к abs_path.
    Если вычислить не удаётся (например, разные диски на Windows) —
    возвращает abs_path как есть, не падая с ValueError.
    """
    try:
        return abs_path.relative_to(root)
    except ValueError:
        return abs_path


def normalize_extension(ext: str) -> str:
    """
    Приводит расширение к стандартному виду: нижний регистр, с точкой.

    Examples:
        "PNG"  → ".png"
        ".Py"  → ".py"
        "exe"  → ".exe"
    """
    ext = ext.lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"
    return ext


def parse_list_text(text: str) -> list[str]:
    """
    Разбирает многострочный текст из QPlainTextEdit в список правил.
    Поддерживает разделители: перенос строки, запятая, точка с запятой.
    Убирает пустые строки и пробелы по краям.

    Examples:
        "node_modules\\nvenv\\n__pycache__" → ["node_modules", "venv", "__pycache__"]
        ".exe, .dll, .png"                 → [".exe", ".dll", ".png"]
    """
    text = text.replace(",", "\n").replace(";", "\n")
    return [
        token.strip()
        for token in text.splitlines()
        if token.strip()
    ]