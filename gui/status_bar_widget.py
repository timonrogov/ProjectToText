# gui/status_bar_widget.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QFrame,
)

from core.models import GenerationResult


class StatusBarWidget(QWidget):
    """
    Нижняя информационная панель.

    Отображает:
    - Прогресс-бар (активен во время сканирования / генерации)
    - Статистику: файлы / размер / токены (с цветовой индикацией)
    - Кнопку «Отчёт о пропущенных файлах»

    Сигналы:
        report_requested — пользователь нажал кнопку отчёта
    """

    report_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(44)
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # --- Прогресс-бар ---
        self._progress = QProgressBar()
        self._progress.setObjectName("statusProgress")
        self._progress.setFixedWidth(180)
        self._progress.setFixedHeight(16)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # --- Статус-текст (пока идёт сканирование) ---
        self._lbl_status = QLabel("Готов к работе")
        self._lbl_status.setObjectName("statusLabel")
        layout.addWidget(self._lbl_status)

        layout.addStretch()

        # --- Файлы ---
        lbl_files_title = QLabel("Файлов:")
        lbl_files_title.setObjectName("statusTitle")
        self._lbl_files = QLabel("—")
        self._lbl_files.setObjectName("statusValue")
        layout.addWidget(lbl_files_title)
        layout.addWidget(self._lbl_files)

        self._add_separator(layout)

        # --- Размер ---
        lbl_size_title = QLabel("Размер:")
        lbl_size_title.setObjectName("statusTitle")
        self._lbl_size = QLabel("—")
        self._lbl_size.setObjectName("statusValue")
        layout.addWidget(lbl_size_title)
        layout.addWidget(self._lbl_size)

        self._add_separator(layout)

        # --- Токены ---
        lbl_tokens_title = QLabel("Токены:")
        lbl_tokens_title.setObjectName("statusTitle")
        self._lbl_tokens = QLabel("—")
        self._lbl_tokens.setObjectName("statusValue")
        layout.addWidget(lbl_tokens_title)
        layout.addWidget(self._lbl_tokens)

        self._add_separator(layout)

        # --- Кнопка отчёта ---
        self._btn_report = QPushButton("📄 Пропущенные файлы")
        self._btn_report.setObjectName("btnReport")
        self._btn_report.setMaximumHeight(28)
        self._btn_report.setVisible(False)
        self._btn_report.clicked.connect(self.report_requested.emit)
        layout.addWidget(self._btn_report)

    @staticmethod
    def _add_separator(layout: QHBoxLayout) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("statusSeparator")
        layout.addWidget(sep)

    # ------------------------------------------------------------------
    # Публичные методы (вызываются из MainWindow)
    # ------------------------------------------------------------------

    def update_stats(self, result: GenerationResult, token_level: str = "green") -> None:
        """Обновляет все метки статистики после генерации / оценки."""
        self._lbl_files.setText(
            f"{result.included_files} / {result.total_files}"
        )
        self._lbl_size.setText(result.size_human)

        # Форматирование токенов
        count = result.token_count
        if count >= 1_000_000:
            token_text = f"~{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            token_text = f"~{count // 1_000}K"
        else:
            token_text = f"~{count}"
        self._lbl_tokens.setText(token_text)

        # Цветовая индикация токенов
        color_map = {
            "green":  "#4caf50",
            "yellow": "#ffb300",
            "red":    "#ef5350",
        }
        color = color_map.get(token_level, "#d4d4d4")
        self._lbl_tokens.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Показываем кнопку отчёта если есть пропущенные
        has_skipped = len(result.skipped_files) > 0
        self._btn_report.setVisible(has_skipped)
        if has_skipped:
            self._btn_report.setText(
                f"📄 Пропущенных: {len(result.skipped_files)}"
            )

        self._lbl_status.setText("✅ Готово")

    def set_status(self, text: str) -> None:
        """Устанавливает текст статуса (например, 'Сканирование...')."""
        self._lbl_status.setText(text)

    def show_progress(self, visible: bool) -> None:
        self._progress.setVisible(visible)
        if visible:
            self._progress.setRange(0, 0)  # Режим «анимации ожидания» (indeterminate)

    def set_progress(self, value: int, maximum: int = 100) -> None:
        """Устанавливает конкретный прогресс (для детерминированных операций)."""
        self._progress.setRange(0, maximum)
        self._progress.setValue(value)

    def reset(self) -> None:
        """Сбрасывает статус-бар к начальному состоянию."""
        self._lbl_status.setText("Готов к работе")
        self._lbl_files.setText("—")
        self._lbl_size.setText("—")
        self._lbl_tokens.setText("—")
        self._lbl_tokens.setStyleSheet("")
        self._progress.setVisible(False)
        self._btn_report.setVisible(False)