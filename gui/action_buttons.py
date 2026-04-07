# gui/action_buttons.py
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
)


class ActionButtons(QWidget):
    """
    Блок крупных кнопок в нижней части правой панели.

    Сигналы:
        estimate_requested   — нажата кнопка «Оценить размер»
        generate_requested   — нажата кнопка «Сгенерировать файл»
        copy_requested       — нажата кнопка «Скопировать в буфер»
    """

    estimate_requested = pyqtSignal()
    generate_requested = pyqtSignal()
    copy_requested     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        layout.addWidget(line)

        # Кнопка «Оценить»
        self._btn_estimate = QPushButton("⚡  Оценить размер")
        self._btn_estimate.setObjectName("btnEstimate")
        self._btn_estimate.setMinimumHeight(36)
        self._btn_estimate.setToolTip(
            "Быстро подсчитать токены и размер вывода\nбез создания файла"
        )
        self._btn_estimate.clicked.connect(self.estimate_requested.emit)
        layout.addWidget(self._btn_estimate)

        # Нижний ряд: «Сгенерировать» + «Скопировать»
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        self._btn_generate = QPushButton("💾  Сгенерировать файл")
        self._btn_generate.setObjectName("btnGenerate")
        self._btn_generate.setMinimumHeight(42)
        self._btn_generate.setToolTip("Сохранить итоговый текст в файл (.txt / .md / .xml)")
        self._btn_generate.clicked.connect(self.generate_requested.emit)

        self._btn_copy = QPushButton("📋  Копировать")
        self._btn_copy.setObjectName("btnCopy")
        self._btn_copy.setMinimumHeight(42)
        self._btn_copy.setMaximumWidth(130)
        self._btn_copy.setToolTip("Сгенерировать и скопировать текст в буфер обмена")
        self._btn_copy.clicked.connect(self.copy_requested.emit)

        bottom_row.addWidget(self._btn_generate, stretch=2)
        bottom_row.addWidget(self._btn_copy,     stretch=1)

        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Управление состоянием кнопок (блокировка во время работы воркера)
    # ------------------------------------------------------------------

    def set_busy(self, busy: bool) -> None:
        """Блокирует/разблокирует кнопки во время фоновой обработки."""
        for btn in (self._btn_estimate, self._btn_generate, self._btn_copy):
            btn.setEnabled(not busy)

        if busy:
            self._btn_generate.setText("⏳  Обработка...")
        else:
            self._btn_generate.setText("💾  Сгенерировать файл")