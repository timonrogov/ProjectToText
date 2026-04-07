# gui/skipped_files_dialog.py
from __future__ import annotations

import csv
from pathlib import Path

from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QComboBox, QLabel, QPushButton,
    QHeaderView, QFileDialog, QMessageBox,
    QAbstractItemView,
)
from PyQt6.QtGui import QColor

from core.models import SkippedFile, SkipReason


# Цвет строки в зависимости от причины пропуска
_ROW_COLORS: dict[SkipReason, str] = {
    SkipReason.BLACKLIST:  "#3e2020",   # тёмно-красный
    SkipReason.SIZE:       "#3e3020",   # тёмно-жёлтый
    SkipReason.BINARY:     "#202030",   # тёмно-синий
    SkipReason.EXTENSION:  "#202530",   # тёмно-серо-синий
    SkipReason.PERMISSION: "#3e2d10",   # тёмно-оранжевый
}


class SkippedFilesDialog(QDialog):
    """
    Диалоговое окно с детализацией пропущенных файлов.

    Функции:
    - Таблица с сортировкой по клику на заголовок
    - Фильтрация по причине пропуска через ComboBox
    - Экспорт в CSV
    """

    def __init__(self, skipped: list[SkippedFile], parent=None):
        super().__init__(parent)
        self._all_skipped = skipped
        self._build_ui()
        self._populate_table(skipped)

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("📄 Отчёт о пропущенных файлах")
        self.setMinimumSize(800, 500)
        self.resize(950, 600)
        self.setObjectName("skippedDialog")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # --- Заголовок и фильтр ---
        top_row = QHBoxLayout()

        lbl_total = QLabel(f"Всего пропущено: <b>{len(self._all_skipped)}</b> файлов")
        lbl_total.setObjectName("dialogHeader")
        top_row.addWidget(lbl_total)
        top_row.addStretch()

        top_row.addWidget(QLabel("Фильтр по причине:"))

        self._filter_combo = QComboBox()
        self._filter_combo.setObjectName("filterCombo")
        self._filter_combo.setMinimumWidth(200)

        # Подсчёт файлов по каждой причине
        from collections import Counter
        counts = Counter(f.reason for f in self._all_skipped)

        self._filter_combo.addItem(f"Все ({len(self._all_skipped)})", userData=None)
        for reason in SkipReason:
            if counts[reason] > 0:
                self._filter_combo.addItem(
                    f"{reason.value} ({counts[reason]})",
                    userData=reason,
                )

        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        top_row.addWidget(self._filter_combo)

        layout.addLayout(top_row)

        # --- Таблица ---
        self._table = QTableWidget()
        self._table.setObjectName("skippedTable")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            "Имя файла", "Путь", "Размер (KB)", "Причина пропуска"
        ])

        # Настройки таблицы
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(False)  # Используем собственную раскраску по причине
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setColumnWidth(0, 200)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 170)

        layout.addWidget(self._table, stretch=1)

        # --- Нижние кнопки ---
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        btn_export = QPushButton("📊 Экспорт в CSV")
        btn_export.setObjectName("btnSmall")
        btn_export.clicked.connect(self._on_export_csv)
        bottom_row.addWidget(btn_export)

        btn_close = QPushButton("Закрыть")
        btn_close.setObjectName("btnGenerate")
        btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Заполнение таблицы
    # ------------------------------------------------------------------

    def _populate_table(self, skipped: list[SkippedFile]) -> None:
        """Заполняет таблицу переданным списком файлов."""
        self._table.setSortingEnabled(False)    # Отключаем сортировку во время заполнения
        self._table.setRowCount(len(skipped))

        for row, sf in enumerate(skipped):
            items = [
                QTableWidgetItem(sf.name),
                QTableWidgetItem(sf.rel_path),
                self._make_size_item(sf.size_kb),
                QTableWidgetItem(sf.reason.value),
            ]

            # Цвет строки по причине
            bg_color = QColor(_ROW_COLORS.get(sf.reason, "#1e1e2e"))
            for col, item in enumerate(items):
                item.setBackground(bg_color)
                item.setForeground(QColor("#d4d4d4"))
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)

    @staticmethod
    def _make_size_item(size_kb: float) -> QTableWidgetItem:
        """
        Специальный элемент таблицы для размера — сортируется как число,
        но отображается как строка.
        """
        item = QTableWidgetItem()
        item.setData(Qt.ItemDataRole.DisplayRole, f"{size_kb:.2f}")
        item.setData(Qt.ItemDataRole.UserRole, size_kb)  # Числовые данные для сортировки
        return item

    # ------------------------------------------------------------------
    # Слоты
    # ------------------------------------------------------------------

    def _on_filter_changed(self, index: int) -> None:
        reason = self._filter_combo.currentData()
        if reason is None:
            filtered = self._all_skipped
        else:
            filtered = [f for f in self._all_skipped if f.reason == reason]
        self._populate_table(filtered)

    def _on_export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            "skipped_files_report.csv",
            "CSV файлы (*.csv)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Имя файла", "Путь", "Размер (KB)", "Причина"])
                for sf in self._all_skipped:
                    writer.writerow([
                        sf.name,
                        sf.rel_path,
                        f"{sf.size_kb:.2f}",
                        sf.reason.value,
                    ])

            QMessageBox.information(
                self,
                "Экспорт завершён",
                f"Отчёт сохранён:\n{path}",
            )
        except OSError as e:
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить файл:\n{e}",
            )