# gui/file_tree_model.py
from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractItemModel, QModelIndex, Qt, QVariant,
)
from PyQt6.QtGui import QColor, QFont, QBrush

from core.models import FileNode, CheckState, ScanResult


# Цвета для визуальной индикации
_COLOR_WHITELIST  = QColor("#4caf50")   # Зелёный — белый список
_COLOR_BLACKLIST  = QColor("#ef5350")   # Красный — чёрный список
_COLOR_PERMISSION = QColor("#ff9800")   # Оранжевый — нет доступа
_COLOR_DEFAULT    = QColor("#d4d4d4")   # Светло-серый — обычный текст (тёмная тема)


class FileTreeModel(QAbstractItemModel):
    """
    Кастомная модель Qt для отображения дерева FileNode в QTreeView.

    Поддерживает:
    - Tri-state чекбоксы (Checked / Unchecked / PartiallyChecked)
    - Цветовую подсветку белого и чёрного списков
    - Зачёркивание файлов из чёрного списка
    - Каскадное (рекурсивное) снятие/постановку галочек
    """

    # Маппинг CheckState (core) → Qt.CheckState (GUI)
    _CHECK_MAP = {
        CheckState.CHECKED:           Qt.CheckState.Checked,
        CheckState.UNCHECKED:         Qt.CheckState.Unchecked,
        CheckState.PARTIALLY_CHECKED: Qt.CheckState.PartiallyChecked,
    }
    _CHECK_MAP_REVERSE = {v: k for k, v in _CHECK_MAP.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root: FileNode | None = None

    # ------------------------------------------------------------------
    # Заполнение модели данными
    # ------------------------------------------------------------------

    def populate(self, scan_result: ScanResult) -> None:
        """Загружает новое дерево в модель. Вызывается из MainWindow после сканирования."""
        self.beginResetModel()
        self._root = scan_result.root
        self.endResetModel()

    def clear(self) -> None:
        """Очищает модель."""
        self.beginResetModel()
        self._root = None
        self.endResetModel()

    def refresh_visuals(self) -> None:
        """
        Обновляет только отображение (цвета, зачёркивание) без перестройки дерева.
        Вызывается после изменения белого/чёрного списка в SettingsPanel.
        """
        if self._root:
            top_left = self.index(0, 0, QModelIndex())
            # Сигнализируем о полном обновлении всех данных
            self.dataChanged.emit(
                top_left,
                self.index(self.rowCount(QModelIndex()) - 1, 0, QModelIndex()),
                [Qt.ItemDataRole.ForegroundRole,
                 Qt.ItemDataRole.FontRole,
                 Qt.ItemDataRole.DecorationRole],
            )

    # ------------------------------------------------------------------
    # Обязательный интерфейс QAbstractItemModel
    # ------------------------------------------------------------------

    def index(self, row: int, col: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, col, parent):
            return QModelIndex()

        parent_node = self._node_from_index(parent)
        if parent_node is None:
            return QModelIndex()

        if row < len(parent_node.children):
            child = parent_node.children[row]
            return self.createIndex(row, col, child)

        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_node: FileNode = index.internalPointer()
        parent_node = self._find_parent(self._root, child_node)

        if parent_node is None or parent_node is self._root:
            return QModelIndex()

        # Находим позицию parent_node в его родителе
        grandparent = self._find_parent(self._root, parent_node)
        if grandparent is None:
            return QModelIndex()

        try:
            row = grandparent.children.index(parent_node)
        except ValueError:
            return QModelIndex()

        return self.createIndex(row, 0, parent_node)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        node = self._node_from_index(parent)
        if node is None:
            return 0
        return len(node.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        node: FileNode = index.internalPointer()

        # --- Отображаемый текст ---
        if role == Qt.ItemDataRole.DisplayRole:
            if node.is_dir:
                return f"📁 {node.name}"
            size_str = f"  ({node.size_kb:.1f} KB)" if node.size_bytes > 0 else ""
            return f"📄 {node.name}{size_str}"

        # --- Состояние чекбокса ---
        if role == Qt.ItemDataRole.CheckStateRole:
            return self._CHECK_MAP.get(node.check_state, Qt.CheckState.Unchecked)

        # --- Цвет текста ---
        if role == Qt.ItemDataRole.ForegroundRole:
            if node.has_permission_error:
                return QBrush(_COLOR_PERMISSION)
            if node.in_whitelist:
                return QBrush(_COLOR_WHITELIST)
            if node.in_blacklist:
                return QBrush(_COLOR_BLACKLIST)
            return QBrush(_COLOR_DEFAULT)

        # --- Шрифт (зачёркивание для чёрного списка) ---
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if node.in_blacklist:
                font.setStrikeOut(True)
            return font

        # --- Тултип ---
        if role == Qt.ItemDataRole.ToolTipRole:
            parts = [str(node.abs_path)]
            if node.has_permission_error:
                parts.append("⚠️ Нет прав доступа")
            if node.in_whitelist:
                parts.append("✅ В белом списке")
            if node.in_blacklist:
                parts.append("❌ В чёрном списке")
            if not node.is_dir:
                parts.append(f"Размер: {node.size_kb:.2f} KB")
            return "\n".join(parts)

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.CheckStateRole:
            return False

        node: FileNode = index.internalPointer()
        qt_state = Qt.CheckState(value)
        core_state = self._CHECK_MAP_REVERSE.get(qt_state, CheckState.CHECKED)

        # Применяем рекурсивно
        self._set_check_recursive(node, core_state)

        # Обновляем состояния родителей вверх по дереву
        self._update_parent_states(index)

        # Сигнализируем об изменении — перерисовать всё дерево
        self.dataChanged.emit(
            self.index(0, 0, QModelIndex()),
            self.index(self.rowCount(QModelIndex()) - 1, 0, QModelIndex()),
            [Qt.ItemDataRole.CheckStateRole],
        )
        return True

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _node_from_index(self, index: QModelIndex) -> FileNode | None:
        """Возвращает узел по индексу. Для невалидного индекса — корень."""
        if not index.isValid():
            return self._root
        return index.internalPointer()

    def _find_parent(self, current: FileNode, target: FileNode) -> FileNode | None:
        """Ищет родительский узел для target в поддереве current."""
        for child in current.children:
            if child is target:
                return current
            if child.is_dir:
                result = self._find_parent(child, target)
                if result is not None:
                    return result
        return None

    def _set_check_recursive(self, node: FileNode, state: CheckState) -> None:
        """Рекурсивно устанавливает состояние чекбокса для узла и всех потомков."""
        # Для рекурсивного вызова используем только Checked / Unchecked
        if state == CheckState.PARTIALLY_CHECKED:
            state = CheckState.CHECKED
        node.check_state = state
        for child in node.children:
            self._set_check_recursive(child, state)

    def _update_parent_states(self, child_index: QModelIndex) -> None:
        """Обновляет состояние родителей вверх по дереву после изменения дочернего."""
        parent_index = self.parent(child_index)
        while parent_index.isValid():
            parent_node: FileNode = parent_index.internalPointer()
            children_states = {c.check_state for c in parent_node.children}

            if children_states == {CheckState.CHECKED}:
                parent_node.check_state = CheckState.CHECKED
            elif children_states == {CheckState.UNCHECKED}:
                parent_node.check_state = CheckState.UNCHECKED
            else:
                parent_node.check_state = CheckState.PARTIALLY_CHECKED

            parent_index = self.parent(parent_index)

    def get_root_node(self) -> FileNode | None:
        return self._root