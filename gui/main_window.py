# gui/main_window.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QSplitter,
    QVBoxLayout, QHBoxLayout,
    QApplication, QMessageBox,
    QFileDialog,
)

from core import ProfileManager, Profile
from core.filter_engine import FilterEngine
from core.models import GenerationResult, ScanResult

from gui.file_tree_panel      import FileTreePanel
from gui.settings_panel       import SettingsPanel
from gui.output_panel         import OutputPanel
from gui.action_buttons       import ActionButtons
from gui.status_bar_widget    import StatusBarWidget
from gui.menu_bar             import AppMenuBar
from gui.skipped_files_dialog import SkippedFilesDialog

from workers.scan_worker     import ScanWorker
from workers.generate_worker import GenerateWorker


class MainWindow(QMainWindow):
    """
    Главное окно приложения. Выступает контроллером (MVC):
    - Создаёт и размещает все дочерние виджеты.
    - Управляет жизненным циклом фоновых воркеров.
    - Связывает сигналы GUI → бизнес-логика и обратно.
    """

    def __init__(self):
        super().__init__()

        # --- Состояние ---
        self._profile_manager  = ProfileManager()
        self._current_profile: Profile | None = None
        self._last_scan_result: ScanResult | None = None
        self._last_gen_result: GenerationResult | None = None

        # Активные воркеры (храним ссылки, чтобы Qt не собрал их GC)
        self._scan_worker: ScanWorker | None       = None
        self._generate_worker: GenerateWorker | None = None

        # Флаг: идёт ли фоновая задача
        self._busy = False

        # --- Инициализация ---
        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._load_default_profile()

    # ================================================================
    # Инициализация окна
    # ================================================================

    def _init_window(self) -> None:
        self.setWindowTitle("LLM Context Builder")
        self.setMinimumSize(1100, 600)
        self.resize(1300, 740)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width()  - self.width())  // 2,
                (geo.height() - self.height()) // 2,
            )

    # ================================================================
    # Построение UI (без изменений относительно Фазы 4, приведён полностью)
    # ================================================================

    def _build_ui(self) -> None:
        # --- Меню ---
        self._menu_bar = AppMenuBar(self)
        self.setMenuBar(self._menu_bar)

        # --- Центральный виджет ---
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Сплиттер ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(6)
        root_layout.addWidget(self._splitter, stretch=1)

        # Левая панель
        self._file_tree_panel = FileTreePanel()
        self._splitter.addWidget(self._file_tree_panel)

        # Правая панель
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        self._settings_panel = SettingsPanel()
        self._output_panel   = OutputPanel()
        self._action_buttons = ActionButtons()

        right_layout.addWidget(self._settings_panel, stretch=3)
        right_layout.addWidget(self._output_panel,   stretch=0)
        right_layout.addWidget(self._action_buttons, stretch=0)

        self._splitter.addWidget(right_panel)
        self._splitter.setSizes([450, 550])

        # Нижний статус-бар
        self._status_bar = StatusBarWidget()
        root_layout.addWidget(self._status_bar)

    # ================================================================
    # Подключение сигналов
    # ================================================================

    def _connect_signals(self) -> None:
        """
        Центральный метод: связывает ВСЕ сигналы GUI со слотами.
        Вызывается один раз после _build_ui().
        """

        # --- Файловый менеджер ---
        self._file_tree_panel.project_folder_requested.connect(
            self._on_project_folder_selected
        )
        self._file_tree_panel.add_to_whitelist.connect(
            self._on_add_to_whitelist
        )
        self._file_tree_panel.add_to_blacklist.connect(
            self._on_add_to_blacklist
        )
        self._file_tree_panel.remove_from_lists.connect(
            self._on_remove_from_lists
        )

        # --- Настройки: изменение любого поля → обновить подсветку дерева ---
        # Используем таймер (debounce 400 мс), чтобы не перерисовывать
        # дерево при каждом нажатии клавиши
        self._highlight_timer = QTimer()
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.setInterval(400)
        self._highlight_timer.timeout.connect(self._refresh_tree_highlights)

        self._settings_panel.settings_changed.connect(
            self._highlight_timer.start
        )

        # --- Кнопки действий ---
        self._action_buttons.estimate_requested.connect(self._on_estimate)
        self._action_buttons.generate_requested.connect(self._on_generate)
        self._action_buttons.copy_requested.connect(self._on_copy)

        # --- Статус-бар: кнопка отчёта ---
        self._status_bar.report_requested.connect(self._on_show_report)

        # --- Меню ---
        self._menu_bar.act_open.triggered.connect(
            self._file_tree_panel._on_select_folder_clicked
        )
        self._menu_bar.act_save_profile.triggered.connect(self._on_save_profile)
        self._menu_bar.act_load_profile.triggered.connect(self._on_load_profile)
        self._menu_bar.act_reset_profile.triggered.connect(self._load_default_profile)

    # ================================================================
    # Слоты: Файловый менеджер
    # ================================================================

    def _on_project_folder_selected(self) -> None:
        """Запускает сканирование выбранной папки."""
        path_str = self._file_tree_panel.get_selected_path()
        if not path_str:
            return

        root_path = Path(path_str)
        if not root_path.is_dir():
            self._show_error("Ошибка", f"Не удалось открыть папку:\n{path_str}")
            return

        self._start_scan(root_path)

    def _on_add_to_whitelist(self, rel_path: str) -> None:
        self._settings_panel.add_to_whitelist(rel_path)
        # Немедленно обновляем подсветку (не ждём таймер)
        self._refresh_tree_highlights()

    def _on_add_to_blacklist(self, name: str) -> None:
        self._settings_panel.add_to_blacklist(name)
        self._refresh_tree_highlights()

    def _on_remove_from_lists(self, name: str) -> None:
        self._settings_panel.remove_from_lists(name)
        self._refresh_tree_highlights()

    # ================================================================
    # Слоты: Кнопки действий
    # ================================================================

    def _on_estimate(self) -> None:
        """«Оценить размер» — генерация только в памяти, без сохранения файла."""
        if not self._check_scan_done():
            return
        self._start_generation(estimate_only=True)

    def _on_generate(self) -> None:
        """«Сгенерировать файл» — генерация + диалог сохранения."""
        if not self._check_scan_done():
            return
        self._start_generation(estimate_only=False)

    def _on_copy(self) -> None:
        """«Скопировать в буфер» — генерация + копирование в clipboard."""
        if not self._check_scan_done():
            return
        self._start_generation(estimate_only=False, copy_mode=True)

    def _on_show_report(self) -> None:
        """Открывает диалог с отчётом о пропущенных файлах."""
        if self._last_gen_result and self._last_gen_result.skipped_files:
            dialog = SkippedFilesDialog(
                self._last_gen_result.skipped_files, parent=self
            )
            dialog.exec()

    # ================================================================
    # Слоты: Профили (Меню)
    # ================================================================

    def _on_save_profile(self) -> None:
        """Сохраняет текущие настройки GUI в .json файл."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить профиль настроек",
            str(Path("profiles") / "my_profile.json"),
            "JSON профиль (*.json)",
        )
        if not path:
            return

        profile = self._collect_profile_from_ui()
        try:
            self._profile_manager.save(profile, Path(path))
            self._status_bar.set_status(f"✅ Профиль сохранён: {Path(path).name}")
        except OSError as e:
            self._show_error("Ошибка сохранения", f"Не удалось сохранить профиль:\n{e}")

    def _on_load_profile(self) -> None:
        """Загружает профиль из .json файла и применяет к GUI."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить профиль настроек",
            "profiles",
            "JSON профиль (*.json)",
        )
        if not path:
            return

        try:
            profile = self._profile_manager.load(Path(path))
        except FileNotFoundError:
            self._show_error("Ошибка", f"Файл не найден:\n{path}")
            return
        except ValueError as e:
            self._show_error("Ошибка формата", f"Некорректный JSON:\n{e}")
            return

        self._apply_profile_to_ui(profile)
        self._status_bar.set_status(
            f"📥 Профиль загружен: {profile.profile_name}"
        )

    def _load_default_profile(self) -> None:
        """Загружает и применяет встроенный профиль по умолчанию."""
        profile = self._profile_manager.load_default()
        self._apply_profile_to_ui(profile)
        self._status_bar.set_status("🔄 Настройки сброшены к значениям по умолчанию")

    # ================================================================
    # Запуск воркеров
    # ================================================================

    def _start_scan(self, root_path: Path) -> None:
        """Создаёт и запускает ScanWorker."""
        if self._busy:
            return

        self._set_busy(True, "Сканирование...")

        # Безопасно останавливаем предыдущий воркер (если был)
        if self._scan_worker is not None:
            self._scan_worker.quit()
            self._scan_worker.wait(2000)

        self._scan_worker = ScanWorker(root_path, parent=self)
        self._scan_worker.scan_complete.connect(self._on_scan_complete)
        self._scan_worker.scan_error.connect(self._on_scan_error)
        self._scan_worker.status_update.connect(self._status_bar.set_status)
        self._scan_worker.finished.connect(lambda: self._set_busy(False))
        self._scan_worker.start()

    def _start_generation(
        self,
        estimate_only: bool = False,
        copy_mode: bool = False,
    ) -> None:
        """
        Создаёт и запускает GenerateWorker.

        Args:
            estimate_only: True — только оценить, False — полная генерация.
            copy_mode:     True — после генерации скопировать в буфер обмена.
        """
        if self._busy:
            return

        root_node = self._file_tree_panel.model.get_root_node()
        if root_node is None:
            return

        profile = self._collect_profile_from_ui()
        action  = "Оцениваю" if estimate_only else "Генерирую"
        self._set_busy(True, f"{action}...")

        if self._generate_worker is not None:
            self._generate_worker.quit()
            self._generate_worker.wait(2000)

        self._generate_worker = GenerateWorker(
            root_node, profile, estimate_only, parent=self
        )

        # Используем lambda для передачи доп. флага copy_mode в слот
        self._generate_worker.generation_complete.connect(
            lambda result, level: self._on_generation_complete(
                result, level, estimate_only, copy_mode
            )
        )
        self._generate_worker.generation_error.connect(self._on_generation_error)
        self._generate_worker.status_update.connect(self._status_bar.set_status)
        self._generate_worker.finished.connect(lambda: self._set_busy(False))
        self._generate_worker.start()

    # ================================================================
    # Слоты воркеров
    # ================================================================

    def _on_scan_complete(self, result: ScanResult) -> None:
        """Вызывается в GUI-потоке после завершения сканирования."""
        self._last_scan_result = result

        # Обновляем модель дерева
        self._file_tree_panel.populate(result)

        # Применяем разметку белого/чёрного списка на только что построенном дереве
        self._refresh_tree_highlights()

        self._status_bar.set_status(
            f"✅ Сканирование завершено: "
            f"{result.total_files} файлов, "
            f"{result.total_dirs} папок "
            f"({result.scan_duration_ms:.0f} мс)"
        )

    def _on_scan_error(self, message: str) -> None:
        """Вызывается в GUI-потоке при ошибке сканирования."""
        self._show_error("Ошибка сканирования", message)
        self._status_bar.set_status("❌ Ошибка сканирования")

    def _on_generation_complete(
        self,
        result: GenerationResult,
        token_level: str,
        estimate_only: bool,
        copy_mode: bool,
    ) -> None:
        """Вызывается в GUI-потоке после завершения генерации."""
        self._last_gen_result = result

        # Обновляем статус-бар
        self._status_bar.update_stats(result, token_level)

        if copy_mode:
            # Режим «Скопировать в буфер»
            self._copy_to_clipboard(result.text)
        elif not estimate_only:
            # Режим «Сгенерировать файл» — открываем диалог сохранения
            self._save_result_to_file(result)

    def _on_generation_error(self, message: str) -> None:
        """Вызывается в GUI-потоке при ошибке генерации."""
        self._show_error("Ошибка генерации", message)
        self._status_bar.set_status("❌ Ошибка генерации")

    # ================================================================
    # Вспомогательные методы
    # ================================================================

    def _collect_profile_from_ui(self, profile_name: str = "Current") -> Profile:
        """
        Собирает объект Profile из текущего состояния всех панелей GUI.
        Вызывается непосредственно перед запуском GenerateWorker.
        """
        settings = self._settings_panel.get_settings()
        output   = self._output_panel.get_output_settings()

        return self._profile_manager.build_profile_from_ui(
            profile_name        = profile_name,
            max_file_size_kb    = settings["max_file_size_kb"],
            whitelist_text      = settings["whitelist_text"],
            blacklist_text      = settings["blacklist_text"],
            extensions_text     = settings["extensions_text"],
            output_format       = output["output_format"],
            remove_empty_lines  = output["remove_empty_lines"],
            include_file_stats  = output["include_file_stats"],
        )

    def _apply_profile_to_ui(self, profile: Profile) -> None:
        """Применяет объект Profile ко всем панелям GUI."""
        self._current_profile = profile
        self._settings_panel.apply_profile(profile)
        self._output_panel.apply_profile(profile)

    def _refresh_tree_highlights(self) -> None:
        """
        Перестраивает разметку белого/чёрного списка на дереве и перерисовывает его.
        Вызывается после любого изменения настроек фильтрации.
        """
        root = self._file_tree_panel.model.get_root_node()
        if root is None:
            return

        # Собираем актуальный профиль и применяем метки к узлам дерева
        profile = self._collect_profile_from_ui()
        engine  = FilterEngine(profile)
        engine.mark_nodes(root)

        # Сигнализируем модели перерисовать цвета (без полного сброса дерева)
        self._file_tree_panel.refresh_visuals()

    def _save_result_to_file(self, result: GenerationResult) -> None:
        """Открывает диалог «Сохранить как...» и записывает итоговый текст."""
        profile = self._collect_profile_from_ui()

        # Предлагаем расширение в зависимости от формата
        ext_map = {"plain": "txt", "markdown": "md", "xml": "xml"}
        default_ext = ext_map.get(profile.output_format.value, "txt")
        filter_str = {
            "txt": "Текстовый файл (*.txt)",
            "md":  "Markdown (*.md)",
            "xml": "XML (*.xml)",
        }.get(default_ext, "Текстовый файл (*.txt)")

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результат",
            f"context.{default_ext}",
            filter_str,
        )
        if not path:
            return

        try:
            Path(path).write_text(result.text, encoding="utf-8")
            self._status_bar.set_status(
                f"✅ Файл сохранён: {Path(path).name}  "
                f"({result.included_files} файлов, {result.size_human})"
            )
        except OSError as e:
            self._show_error(
                "Ошибка сохранения",
                f"Не удалось записать файл:\n{e}"
            )

    def _copy_to_clipboard(self, text: str) -> None:
        """Копирует текст в буфер обмена и показывает уведомление."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # Временное уведомление в статус-баре (сбросится через 3 сек)
        self._status_bar.set_status("📋 Скопировано в буфер обмена!")
        QTimer.singleShot(
            3000,
            lambda: self._status_bar.set_status("✅ Готово")
        )

    def _set_busy(self, busy: bool, status: str = "") -> None:
        """
        Переключает состояние «занято»:
        - Блокирует кнопки действий
        - Показывает / скрывает прогресс-бар
        - Обновляет текст статуса
        """
        self._busy = busy
        self._action_buttons.set_busy(busy)
        self._status_bar.show_progress(busy)
        if status:
            self._status_bar.set_status(status)

    def _check_scan_done(self) -> bool:
        """
        Проверяет, было ли выполнено сканирование.
        Если нет — показывает подсказку пользователю.
        """
        if self._file_tree_panel.model.get_root_node() is None:
            QMessageBox.information(
                self,
                "Папка не выбрана",
                "Сначала выберите папку проекта с помощью кнопки\n"
                "«Выбрать папку проекта» или через меню Файл → Выбрать проект.",
            )
            return False
        if self._busy:
            return False
        return True

    def _show_error(self, title: str, message: str) -> None:
        """Показывает модальный диалог с ошибкой."""
        QMessageBox.critical(self, title, message)

    # ================================================================
    # Закрытие окна
    # ================================================================

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        При закрытии корректно останавливаем фоновые потоки.
        Это предотвращает краш при завершении приложения во время работы воркера.
        """
        for worker in (self._scan_worker, self._generate_worker):
            if worker is not None and worker.isRunning():
                worker.quit()
                worker.wait(3000)   # Ждём завершения максимум 3 секунды
        event.accept()

    # ================================================================
    # Публичный доступ к панелям (для тестов)
    # ================================================================

    @property
    def file_tree_panel(self) -> FileTreePanel:
        return self._file_tree_panel

    @property
    def settings_panel(self) -> SettingsPanel:
        return self._settings_panel

    @property
    def output_panel(self) -> OutputPanel:
        return self._output_panel

    @property
    def action_buttons(self) -> ActionButtons:
        return self._action_buttons

    @property
    def status_bar_widget(self) -> StatusBarWidget:
        return self._status_bar