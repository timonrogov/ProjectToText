# gui/menu_bar.py
from __future__ import annotations

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMenuBar


class AppMenuBar(QMenuBar):
    """
    Верхнее меню приложения.

    Все действия (QAction) доступны как публичные атрибуты,
    чтобы MainWindow мог подключить к ним слоты.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_menus()

    def _build_menus(self) -> None:
        # ==================== Меню «Файл» ====================
        file_menu = self.addMenu("Файл")

        self.act_open = QAction("📂  Выбрать проект...", self)
        self.act_open.setShortcut(QKeySequence("Ctrl+O"))
        self.act_open.setStatusTip("Открыть корневую папку проекта")

        file_menu.addAction(self.act_open)
        file_menu.addSeparator()

        self.act_save_profile = QAction("💾  Сохранить профиль как...", self)
        self.act_save_profile.setShortcut(QKeySequence("Ctrl+S"))
        self.act_save_profile.setStatusTip("Сохранить текущие настройки фильтрации в файл")

        self.act_load_profile = QAction("📥  Загрузить профиль...", self)
        self.act_load_profile.setShortcut(QKeySequence("Ctrl+L"))
        self.act_load_profile.setStatusTip("Загрузить настройки фильтрации из файла")

        self.act_reset_profile = QAction("🔄  Сбросить к настройкам по умолчанию", self)
        self.act_reset_profile.setStatusTip(
            "Восстановить встроенный профиль по умолчанию"
        )

        file_menu.addAction(self.act_save_profile)
        file_menu.addAction(self.act_load_profile)
        file_menu.addSeparator()
        file_menu.addAction(self.act_reset_profile)
        file_menu.addSeparator()

        self.act_quit = QAction("✖  Выход", self)
        self.act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.act_quit.triggered.connect(
            lambda: self.parent().close() if self.parent() else None
        )
        file_menu.addAction(self.act_quit)

        # ==================== Меню «Справка» ====================
        help_menu = self.addMenu("Справка")

        self.act_about = QAction("ℹ️  О программе", self)
        self.act_about.triggered.connect(self._show_about)
        help_menu.addAction(self.act_about)

    def _show_about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self.parent(),
            "О программе",
            "<h3>LLM Context Builder</h3>"
            "<p>Инструмент для агрегации исходного кода "
            "в единый текстовый контекст для LLM.</p>"
            "<p>Стек: Python 3.10+, PyQt6, tiktoken, pathspec</p>",
        )