# core/scanner.py
from __future__ import annotations

import os
import time
from pathlib import Path

from core.models import FileNode, ScanResult, CheckState


class FileScanner:
    """
    Рекурсивно сканирует директорию и строит дерево FileNode.

    Намеренно НЕ применяет никакой фильтрации — это задача FilterEngine.
    Единственное исключение: перехват PermissionError.
    """

    def scan(self, root_path: Path) -> ScanResult:
        """
        Основной метод сканирования.

        Args:
            root_path: Абсолютный путь к корневой директории проекта.

        Returns:
            ScanResult с заполненным деревом FileNode.
        """
        if not root_path.is_dir():
            raise ValueError(f"Указанный путь не является директорией: {root_path}")

        start_time = time.perf_counter()

        total_files = 0
        total_dirs = 0

        def _build_node(abs_path: Path, rel_path: Path) -> FileNode:
            """Рекурсивно строит узел и все его дочерние узлы."""
            nonlocal total_files, total_dirs

            is_dir = abs_path.is_dir()

            # Получаем размер файла (для папок — 0)
            size_bytes = 0
            if not is_dir:
                try:
                    size_bytes = abs_path.stat().st_size
                except OSError:
                    size_bytes = 0

            node = FileNode(
                abs_path   = abs_path,
                rel_path   = rel_path,
                is_dir     = is_dir,
                size_bytes = size_bytes,
                check_state = CheckState.CHECKED,
            )

            if is_dir:
                total_dirs += 1
                try:
                    # os.scandir быстрее, чем Path.iterdir() на больших директориях
                    entries = sorted(
                        os.scandir(abs_path),
                        key=lambda e: (not e.is_dir(), e.name.lower())
                        # Папки идут первыми, затем файлы — алфавитно
                    )
                    for entry in entries:
                        # Пропускаем все папки, название которых начинается с точки
                        if entry.is_dir() and entry.name.startswith('.'):
                            continue

                        child_abs = Path(entry.path)
                        child_rel = rel_path / entry.name
                        child_node = _build_node(child_abs, child_rel)
                        node.children.append(child_node)

                except PermissionError:
                    # Нет прав на чтение содержимого папки
                    node.has_permission_error = True
            else:
                total_files += 1

            return node

        # Корневой узел — сама выбранная папка; rel_path = Path(".")
        root_node = _build_node(root_path, Path("."))

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ScanResult(
            root             = root_node,
            total_files      = total_files,
            total_dirs       = total_dirs,
            scan_duration_ms = elapsed_ms,
        )

    def collect_all_files(self, root: FileNode) -> list[FileNode]:
        """
        Вспомогательный метод: обходит дерево и возвращает плоский список
        всех файловых узлов (не папок) с состоянием CHECKED.

        Используется GenerateWorker для передачи в TextGenerator.
        """
        result: list[FileNode] = []
        self._collect_recursive(root, result)
        return result

    def _collect_recursive(self, node: FileNode, result: list[FileNode]) -> None:
        if node.is_dir:
            for child in node.children:
                self._collect_recursive(child, result)
        else:
            result.append(node)