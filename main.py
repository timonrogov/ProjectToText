# main.py
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


def load_stylesheet(app: QApplication) -> None:
    qss_path = Path(__file__).parent / "resources" / "styles" / "main.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        print(f"[WARNING] Файл стилей не найден: {qss_path}", file=sys.stderr)


def handle_uncaught_exception(
    exc_type, exc_value, exc_traceback
) -> None:
    """
    Глобальный обработчик необработанных исключений.
    Вместо молчаливого краша показывает пользователю диалог с деталями.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text  = "".join(tb_lines)

    print(f"[UNCAUGHT EXCEPTION]\n{tb_text}", file=sys.stderr)

    # Пытаемся показать диалог, если QApplication уже запущен
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