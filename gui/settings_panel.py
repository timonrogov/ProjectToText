# gui/settings_panel.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QPlainTextEdit, QPushButton,
    QSpinBox, QGroupBox, QCheckBox, QFrame,
)

from core.models import Profile


# Группы расширений для быстрого добавления
_QUICK_GROUPS = {
    "🖼 Медиа":   ".png .jpg .jpeg .gif .bmp .svg .ico .webp .mp4 .mov .avi .mkv .mp3 .wav .ogg",
    "📦 Архивы":  ".zip .rar .7z .tar .gz .bz2",
    "⚙️ Бинарники": ".exe .dll .so .o .a .lib .pyd .class .pyc .jar",
    "📄 Офис":    ".pdf .doc .docx .xls .xlsx .ppt .pptx .odt",
}


class SettingsPanel(QWidget):
    """
    Правая верхняя панель: вкладки с чёрным/белым списком,
    расширениями и лимитом размера файла.

    Сигналы:
        settings_changed — испускается при любом изменении настроек
                           (используется для отложенного обновления подсветки дерева)
    """

    settings_changed = pyqtSignal()

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

        header = QLabel("⚙️ Настройки фильтрации")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # --- Вкладки ---
        self._tabs = QTabWidget()
        self._tabs.setObjectName("settingsTabs")

        self._tabs.addTab(self._build_blacklist_tab(),  "🚫 Чёрный список")
        self._tabs.addTab(self._build_whitelist_tab(),  "✅ Белый список")
        self._tabs.addTab(self._build_extensions_tab(), "📎 Расширения")

        layout.addWidget(self._tabs, stretch=1)

        # --- Лимит размера файла ---
        layout.addWidget(self._build_size_limit_block())

    # ------------------------------------------------------------------
    # Вкладка «Чёрный список»
    # ------------------------------------------------------------------

    def _build_blacklist_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)

        hint = QLabel("Каждое правило — с новой строки.\nПапки и файлы: node_modules, .env, secret.txt")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._blacklist_edit = QPlainTextEdit()
        self._blacklist_edit.setObjectName("listEdit")
        self._blacklist_edit.setPlaceholderText("node_modules\nvenv\n__pycache__\n.env")
        self._blacklist_edit.textChanged.connect(self.settings_changed.emit)
        layout.addWidget(self._blacklist_edit, stretch=1)

        btn_row = self._make_list_buttons(self._blacklist_edit, "blacklist")
        layout.addLayout(btn_row)

        return tab

    # ------------------------------------------------------------------
    # Вкладка «Белый список»
    # ------------------------------------------------------------------

    def _build_whitelist_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)

        hint = QLabel("Файлы здесь включаются принудительно,\nигнорируя чёрный список и лимит размера.")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._whitelist_edit = QPlainTextEdit()
        self._whitelist_edit.setObjectName("listEdit")
        self._whitelist_edit.setPlaceholderText("src/core/important.py\nWeb.config")
        self._whitelist_edit.textChanged.connect(self.settings_changed.emit)
        layout.addWidget(self._whitelist_edit, stretch=1)

        btn_row = self._make_list_buttons(self._whitelist_edit, "whitelist")
        layout.addLayout(btn_row)

        return tab

    # ------------------------------------------------------------------
    # Вкладка «Расширения»
    # ------------------------------------------------------------------

    def _build_extensions_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)

        hint = QLabel("Расширения через пробел или запятую:")
        hint.setObjectName("hintLabel")
        layout.addWidget(hint)

        self._extensions_edit = QPlainTextEdit()
        self._extensions_edit.setObjectName("listEdit")
        self._extensions_edit.setPlaceholderText(".exe .dll .png .mp4 .zip")
        self._extensions_edit.setMaximumHeight(80)
        self._extensions_edit.textChanged.connect(self.settings_changed.emit)
        layout.addWidget(self._extensions_edit)

        # --- Быстрые кнопки добавления групп ---
        quick_label = QLabel("Быстрое добавление групп:")
        quick_label.setObjectName("hintLabel")
        layout.addWidget(quick_label)

        for group_name, extensions in _QUICK_GROUPS.items():
            btn = QPushButton(group_name)
            btn.setObjectName("btnQuick")
            btn.setMaximumHeight(26)
            btn.clicked.connect(lambda checked, exts=extensions: self._add_extensions(exts))
            layout.addWidget(btn)

        layout.addStretch()

        btn_row = self._make_list_buttons(self._extensions_edit, "extensions")
        layout.addLayout(btn_row)

        return tab

    # ------------------------------------------------------------------
    # Блок «Лимит размера»
    # ------------------------------------------------------------------

    def _build_size_limit_block(self) -> QGroupBox:
        group = QGroupBox("Лимит размера файла")
        group.setObjectName("sizeGroup")
        row = QHBoxLayout(group)
        row.setContentsMargins(8, 4, 8, 4)

        row.addWidget(QLabel("Макс. размер:"))

        self._size_spin = QSpinBox()
        self._size_spin.setObjectName("sizeSpin")
        self._size_spin.setRange(1, 102400)
        self._size_spin.setValue(20)
        self._size_spin.setSuffix("  КБ")
        self._size_spin.setMinimumWidth(120)
        self._size_spin.valueChanged.connect(self.settings_changed.emit)
        row.addWidget(self._size_spin)
        row.addStretch()

        return group

    # ------------------------------------------------------------------
    # Вспомогательный метод: кнопки под каждым редактором списка
    # ------------------------------------------------------------------

    def _make_list_buttons(self, editor: QPlainTextEdit, list_type: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)

        btn_clear   = QPushButton("Очистить")
        btn_default = QPushButton("По умолчанию")
        btn_clear.setObjectName("btnSmall")
        btn_default.setObjectName("btnSmall")
        btn_clear.setMaximumHeight(24)
        btn_default.setMaximumHeight(24)

        btn_clear.clicked.connect(editor.clear)

        if list_type == "blacklist":
            btn_default.clicked.connect(self._reset_blacklist_default)
        elif list_type == "whitelist":
            btn_default.clicked.connect(editor.clear)
        elif list_type == "extensions":
            btn_default.clicked.connect(self._reset_extensions_default)

        row.addStretch()
        row.addWidget(btn_clear)
        row.addWidget(btn_default)
        return row

    # ------------------------------------------------------------------
    # Публичные методы (вызываются из MainWindow)
    # ------------------------------------------------------------------

    def apply_profile(self, profile: Profile) -> None:
        """Заполняет все поля из объекта Profile."""
        self._blacklist_edit.setPlainText("\n".join(profile.blacklist))
        self._whitelist_edit.setPlainText("\n".join(profile.whitelist))
        self._extensions_edit.setPlainText(
            " ".join(profile.ignored_extensions)
        )
        self._size_spin.setValue(profile.max_file_size_kb)

    def get_settings(self) -> dict:
        """
        Возвращает текущие значения всех полей в виде словаря.
        Используется ProfileManager.build_profile_from_ui().
        """
        return {
            "blacklist_text":   self._blacklist_edit.toPlainText(),
            "whitelist_text":   self._whitelist_edit.toPlainText(),
            "extensions_text":  self._extensions_edit.toPlainText(),
            "max_file_size_kb": self._size_spin.value(),
        }

    def add_to_whitelist(self, path: str) -> None:
        """Добавляет строку в конец белого списка (вызывается из контекстного меню дерева)."""
        current = self._whitelist_edit.toPlainText().strip()
        if path not in current:
            new_text = f"{current}\n{path}" if current else path
            self._whitelist_edit.setPlainText(new_text.strip())
            self._tabs.setCurrentIndex(1)  # Переключаемся на вкладку «Белый список»

    def add_to_blacklist(self, name: str) -> None:
        """Добавляет строку в конец чёрного списка."""
        current = self._blacklist_edit.toPlainText().strip()
        if name not in current:
            new_text = f"{current}\n{name}" if current else name
            self._blacklist_edit.setPlainText(new_text.strip())
            self._tabs.setCurrentIndex(0)  # Переключаемся на вкладку «Чёрный список»

    def remove_from_lists(self, name: str) -> None:
        """Удаляет запись из обоих списков."""
        for editor in (self._blacklist_edit, self._whitelist_edit):
            lines = [
                l for l in editor.toPlainText().splitlines()
                if l.strip() and l.strip() != name
            ]
            editor.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    # Сброс к значениям по умолчанию
    # ------------------------------------------------------------------

    def _reset_blacklist_default(self) -> None:
        from core import ProfileManager
        default = ProfileManager().load_default()
        self._blacklist_edit.setPlainText("\n".join(default.blacklist))

    def _reset_extensions_default(self) -> None:
        from core import ProfileManager
        default = ProfileManager().load_default()
        self._extensions_edit.setPlainText(" ".join(default.ignored_extensions))

    def _add_extensions(self, exts: str) -> None:
        """Добавляет группу расширений к уже существующим (без дублей)."""
        current_set = set(self._extensions_edit.toPlainText().split())
        new_set     = current_set | set(exts.split())
        self._extensions_edit.setPlainText(" ".join(sorted(new_set)))