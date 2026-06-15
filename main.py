# main.py
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


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


def main() -> None:
    # Устанавливаем глобальный обработчик ДО создания QApplication
    sys.excepthook = handle_uncaught_exception

    # --- ФИКС ИКОНКИ ДЛЯ ПАНЕЛИ ЗАДАЧ WINDOWS ---
    if sys.platform == 'win32':
        import ctypes
        # Строка может быть любой, главное — уникальной
        myappid = 'ProjectToText.1.0.0'
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
    app.setApplicationName("LLM Context Builder")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LLMTools")

    load_stylesheet(app)

    # Импортируем MainWindow здесь, чтобы не делать это до QApplication
    from gui.main_window import MainWindow
    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()