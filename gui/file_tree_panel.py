# gui/file_tree_panel.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeView, QLabel,
    QMenu, QFileDialog, QSizePolicy,
    QAbstractItemView,
)
from PyQt6.QtGui import QAction

from core.models import ScanResult, FileNode
from gui.file_tree_model import FileTreeModel


class FileTreePanel(QWidget):
    """
    Левая панель: кнопка выбора папки + дерево файлов проекта.

    Сигналы:
        project_folder_requested  — пользователь нажал «Выбрать папку»
        add_to_whitelist(str)     — через контекстное меню: добавить путь в белый список
        add_to_blacklist(str)     — через контекстное меню: добавить имя в чёрный список
        remove_from_lists(str)    — удалить из обоих списков
    """

    project_folder_requested = pyqtSignal()
    add_to_whitelist  = pyqtSignal(str)
    add_to_blacklist  = pyqtSignal(str)
    remove_from_lists = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = FileTreeModel()
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 4, 8)
        layout.setSpacing(6)

        # --- Заголовок панели ---
        header = QLabel("📂 Файловый менеджер")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # --- Кнопка выбора папки ---
        self._btn_select = QPushButton("🗁  Выбрать папку проекта")
        self._btn_select.setObjectName("btnSelectFolder")
        self._btn_select.setMinimumHeight(36)
        self._btn_select.clicked.connect(self._on_select_folder_clicked)
        layout.addWidget(self._btn_select)

        # --- Метка текущей папки ---
        self._lbl_path = QLabel("Папка не выбрана")
        self._lbl_path.setObjectName("labelPath")
        self._lbl_path.setWordWrap(True)
        self._lbl_path.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._lbl_path)

        # --- Кнопки «Выбрать всё / Снять всё» ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        # --- Кнопки управления деревом ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._btn_check_all = QPushButton("✓ Всё")
        self._btn_uncheck_all = QPushButton("✗ Снять")
        self._btn_expand_all = QPushButton("➕ Развернуть")
        self._btn_collapse_all = QPushButton("➖ Свернуть")

        # Применяем общие настройки ко всем 4 кнопкам через цикл
        for btn in (self._btn_check_all, self._btn_uncheck_all,
                    self._btn_expand_all, self._btn_collapse_all):
            btn.setObjectName("btnSmall")
            btn.setMaximumHeight(26)
            btn_row.addWidget(btn)

        self._btn_check_all.clicked.connect(self._on_check_all)
        self._btn_uncheck_all.clicked.connect(self._on_uncheck_all)
        self._btn_expand_all.clicked.connect(self._on_expand_all)
        self._btn_collapse_all.clicked.connect(self._on_collapse_all)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # --- QTreeView ---
        self._tree_view = QTreeView()
        self._tree_view.setModel(self._model)
        self._tree_view.setObjectName("fileTreeView")

        # Настройки отображения
        self._tree_view.setHeaderHidden(True)
        self._tree_view.setUniformRowHeights(True)   # Ускоряет рендеринг
        self._tree_view.setAnimated(False)            # Отключаем анимацию для скорости
        self._tree_view.setIndentation(20)
        self._tree_view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # Контекстное меню
        self._tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_view.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._tree_view, stretch=1)

        # --- Легенда ---
        legend = QLabel(
            "<span style='color:#4caf50'>■</span> Белый список &nbsp;"
            "<span style='color:#ef5350'>■</span> Чёрный список &nbsp;"
            "<span style='color:#ff9800'>■</span> Нет доступа"
        )
        legend.setObjectName("legend")
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(legend)

    # ------------------------------------------------------------------
    # Публичные методы (вызываются из MainWindow)
    # ------------------------------------------------------------------

    def populate(self, scan_result: ScanResult) -> None:
        """Загружает результат сканирования в дерево."""
        self._model.populate(scan_result)
        self._tree_view.expandToDepth(1)   # Раскрываем первый уровень

    def set_project_path_label(self, path: str) -> None:
        # Показываем только последние 50 символов пути для экономии места
        display = path if len(path) <= 50 else "…" + path[-47:]
        self._lbl_path.setText(display)
        self._lbl_path.setToolTip(path)

    def refresh_visuals(self) -> None:
        """Перерисовывает цвета узлов (после изменения списков)."""
        self._model.refresh_visuals()

    @property
    def model(self) -> FileTreeModel:
        return self._model

    # ------------------------------------------------------------------
    # Слоты
    # ------------------------------------------------------------------

    def _on_select_folder_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите корневую папку проекта",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.set_project_path_label(folder)
            # Сохраняем путь для использования в MainWindow
            self._selected_path = folder
            self.project_folder_requested.emit()


    def _on_check_all(self) -> None:
        from core.models import CheckState
        root = self._model.get_root_node()
        if root:
            self._set_all_recursive(root, CheckState.CHECKED)
            self._model.beginResetModel()
            self._model.endResetModel()

    def _on_uncheck_all(self) -> None:
        from core.models import CheckState
        root = self._model.get_root_node()
        if root:
            self._set_all_recursive(root, CheckState.UNCHECKED)
            self._model.beginResetModel()
            self._model.endResetModel()

    def _set_all_recursive(self, node: FileNode, state) -> None:
        node.check_state = state
        for child in node.children:
            self._set_all_recursive(child, state)

    def _on_expand_all(self) -> None:
        """Разворачивает все узлы дерева."""
        self._tree_view.expandAll()

    def _on_collapse_all(self) -> None:
        """Сворачивает всё, оставляя открытым только первый уровень (папку проекта)."""
        self._tree_view.collapseAll()
        self._tree_view.expandToDepth(-1)

    # ------------------------------------------------------------------
    # Контекстное меню
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos: QPoint) -> None:
        index = self._tree_view.indexAt(pos)
        if not index.isValid():
            return

        node: FileNode = index.internalPointer()
        rel_path = str(node.rel_path).replace("\\", "/")
        name = node.name

        menu = QMenu(self)
        menu.setObjectName("contextMenu")

        act_whitelist = QAction(f"✅  Добавить в Белый список  ({name})", self)
        act_blacklist = QAction(f"❌  Добавить в Чёрный список ({name})", self)
        act_remove    = QAction(f"🗑️  Удалить из списков", self)

        act_whitelist.triggered.connect(lambda: self.add_to_whitelist.emit(rel_path))
        act_blacklist.triggered.connect(lambda: self.add_to_blacklist.emit(name))
        act_remove.triggered.connect(   lambda: self.remove_from_lists.emit(name))

        menu.addAction(act_whitelist)
        menu.addAction(act_blacklist)
        menu.addSeparator()
        menu.addAction(act_remove)

        menu.exec(self._tree_view.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Геттер для выбранной папки (используется в MainWindow при запуске воркера)
    # ------------------------------------------------------------------

    def get_selected_path(self) -> str | None:
        return getattr(self, "_selected_path", None)