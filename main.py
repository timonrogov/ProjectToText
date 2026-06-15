# main.py
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QPalette, QColor, QMovie
from PyQt6.QtCore import Qt, pyqtSignal


def load_stylesheet(app: QApplication) -> None:
    """Загружает QSS-стили через resource_path (работает и в бандле, и в IDE)."""
    from core.resource_path import resource_path
    qss_path = resource_path("resources/styles/main.qss")
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        print(f"[WARNING] Файл стилей не найден: {qss_path}", file=sys.stderr)


def set_app_icon(app: QApplication) -> None:
    """Устанавливает иконку приложения (в заголовке окна и панели задач)."""
    from core.resource_path import resource_path
    from PyQt6.QtGui import QIcon

    # PyQt прекрасно читает PNG на ЛЮБОЙ ОС (плагины для .ico больше не нужны)
    icon_file = "resources/icons/app_icon.png"

    icon_path = resource_path(icon_file)
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[WARNING] Иконка не найдена: {icon_path}", file=sys.stderr)



def ensure_profiles_dir() -> None:
    """Создаёт папку для пользовательских профилей если её нет."""
    from core.resource_path import get_app_data_dir
    profiles_dir = get_app_data_dir()
    profiles_dir.mkdir(parents=True, exist_ok=True)


def handle_uncaught_exception(exc_type, exc_value, exc_traceback) -> None:
    """Глобальный обработчик: показывает диалог вместо молчаливого краша."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"[UNCAUGHT EXCEPTION]\n{tb_text}", file=sys.stderr)

    app = QApplication.instance()
    if app:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Критическая ошибка")
        msg.setText(
            "Произошла непредвиденная ошибка.\n"
            "Пожалуйста, сообщите о ней разработчику."
        )
        msg.setDetailedText(tb_text)
        msg.exec()


class AnimatedSplashScreen(QWidget):
    """Кастомное прозрачное окно-заставка с анимацией GIF."""
    finished = pyqtSignal()

    # Добавили параметры width и height (по умолчанию 400x400)
    def __init__(self, gif_path: str, width: int = 400, height: int = 400):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 1. Устанавливаем размер окна заставки
        self.resize(width, height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. РАСТЯГИВАЕМ гифку на весь размер QLabel
        self.label.setScaledContents(True)

        layout.addWidget(self.label)

        self.movie = QMovie(gif_path)
        self.label.setMovie(self.movie)

        # 3. Вызываем метод центрирования
        self._center_on_screen()

        self.movie.frameChanged.connect(self._on_frame_changed)
        self._last_frame = -1

    def _center_on_screen(self):
        """Вычисляет центр экрана и перемещает туда заставку."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def start(self):
        self.show()
        self.movie.start()

    def _on_frame_changed(self, frame_num: int):
        total_frames = self.movie.frameCount()

        if (total_frames > 0 and frame_num == total_frames - 1) or frame_num < self._last_frame:
            self.movie.stop()
            self.finished.emit()
            self.close()
            self.deleteLater()

        self._last_frame = frame_num


def main() -> None:
    # Устанавливаем глобальный обработчик ДО создания QApplication
    sys.excepthook = handle_uncaught_exception

    # --- ФИКС ИКОНКИ ДЛЯ ПАНЕЛИ ЗАДАЧ WINDOWS ---
    if sys.platform == 'win32':
        import ctypes
        # Строка может быть любой, главное — уникальной
        myappid = 'ProjectToText.1.5.1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
    # --------------------------------------------

    # High-DPI поддержка (особенно важно на Windows с масштабированием > 100%)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    # --- Включаем стиль Fusion и делаем системные иконки светлыми ---
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#a6adc8"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#a6adc8"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#a6adc8"))
    app.setPalette(palette)
    # ----------------------------------------------------------------
    app.setApplicationName("Project to Text")
    app.setApplicationVersion("1.5.1")
    app.setOrganizationName("RogovLLMTools")

    load_stylesheet(app)
    set_app_icon(app)

    from gui.main_window import MainWindow
    from core.resource_path import resource_path

    # Создаём главное окно, но ПОКА НЕ показываем его (убрали .showMaximized())
    window = MainWindow()

    # Ищем нашу гифку
    gif_path = resource_path("resources/icons/Zoolander Blue Steel GIF.gif")

    if gif_path.exists():
        # Чтобы заставка не "висела" как локальная переменная и не была удалена сборщиком мусора,
        # привязываем её к окну (просто как атрибут)
        window._splash = AnimatedSplashScreen(str(gif_path), width=560, height=466)

        # Как только гифка завершится (сработает finished), показываем главное окно
        window._splash.finished.connect(window.showMaximized)

        # Запускаем анимацию
        window._splash.start()
    else:
        # Если гифки почему-то нет (удалили/переименовали), просто сразу открываем программу
        window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()