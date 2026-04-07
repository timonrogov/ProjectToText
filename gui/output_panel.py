# gui/output_panel.py
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QRadioButton, QCheckBox, QLabel,
)

from core.models import Profile, OutputFormat


class OutputPanel(QWidget):
    """
    Панель выбора формата вывода и опций минификации.

    Сигналы:
        format_changed — пользователь переключил формат
    """

    format_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # --- Формат вывода ---
        fmt_group = QGroupBox("📋 Формат вывода")
        fmt_group.setObjectName("outputGroup")
        fmt_layout = QHBoxLayout(fmt_group)
        fmt_layout.setSpacing(16)

        self._rb_plain    = QRadioButton("Plain Text")
        self._rb_markdown = QRadioButton("Markdown")
        self._rb_xml      = QRadioButton("XML (Claude/GPT-4)")

        self._rb_markdown.setChecked(True)  # По умолчанию

        self._rb_plain.toggled.connect(
            lambda checked: self.format_changed.emit("plain") if checked else None
        )
        self._rb_markdown.toggled.connect(
            lambda checked: self.format_changed.emit("markdown") if checked else None
        )
        self._rb_xml.toggled.connect(
            lambda checked: self.format_changed.emit("xml") if checked else None
        )

        fmt_layout.addWidget(self._rb_plain)
        fmt_layout.addWidget(self._rb_markdown)
        fmt_layout.addWidget(self._rb_xml)
        fmt_layout.addStretch()

        layout.addWidget(fmt_group)

        # --- Опции минификации ---
        mini_group = QGroupBox("✂️ Минификация")
        mini_group.setObjectName("outputGroup")
        mini_layout = QHBoxLayout(mini_group)

        self._cb_empty_lines = QCheckBox("Удалить пустые строки")
        self._cb_stats       = QCheckBox("Статистика в начале файла")
        self._cb_stats.setChecked(True)

        mini_layout.addWidget(self._cb_empty_lines)
        mini_layout.addSpacing(20)
        mini_layout.addWidget(self._cb_stats)
        mini_layout.addStretch()

        layout.addWidget(mini_group)

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def apply_profile(self, profile: Profile) -> None:
        """Применяет настройки из профиля к радиокнопкам и чекбоксам."""
        fmt_map = {
            OutputFormat.PLAIN:    self._rb_plain,
            OutputFormat.MARKDOWN: self._rb_markdown,
            OutputFormat.XML:      self._rb_xml,
        }
        rb = fmt_map.get(profile.output_format, self._rb_markdown)
        rb.setChecked(True)

        self._cb_empty_lines.setChecked(profile.remove_empty_lines)
        self._cb_stats.setChecked(profile.include_file_stats)

    def get_output_settings(self) -> dict:
        """Возвращает текущие настройки вывода."""
        if self._rb_plain.isChecked():
            fmt = "plain"
        elif self._rb_xml.isChecked():
            fmt = "xml"
        else:
            fmt = "markdown"

        return {
            "output_format":      fmt,
            "remove_empty_lines": self._cb_empty_lines.isChecked(),
            "include_file_stats": self._cb_stats.isChecked(),
        }