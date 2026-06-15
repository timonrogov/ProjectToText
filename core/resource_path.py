# core/resource_path.py
"""
Утилита для получения корректных путей к ресурсам приложения.

В режиме разработки (запуск через python main.py):
    Возвращает путь относительно корня проекта.

В собранном бандле (PyInstaller --onefile или --onedir):
    PyInstaller распаковывает ресурсы в sys._MEIPASS (временная папка).
    Все пути ресурсов должны идти через resource_path(), иначе файлы
    не будут найдены и приложение упадёт с FileNotFoundError.

Использование:
    from core.resource_path import resource_path

    qss_path  = resource_path("resources/styles/main.qss")
    icon_path = resource_path("resources/icons/app_icon.ico")
    profile   = resource_path("resources/default_profile.json")
"""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """
    Возвращает абсолютный путь к ресурсу, совместимый
    с режимом разработки и с PyInstaller-бандлом.

    Args:
        relative_path: Путь относительно корня проекта,
                       например "resources/styles/main.qss"

    Returns:
        Абсолютный Path к файлу.
    """
    # sys._MEIPASS существует только внутри PyInstaller-бандла
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        # В режиме разработки: корень проекта = папка, где лежит main.py
        base = Path(__file__).parent.parent

    return base / relative_path


def get_app_data_dir() -> Path:
    """
    Возвращает папку для пользовательских данных (профилей).
    В отличие от resource_path, эта папка ЗАПИСЫВАЕМАЯ — она находится
    рядом с исполняемым файлом (или в корне проекта при разработке).

    Профили нельзя хранить в sys._MEIPASS — эта папка пересоздаётся
    при каждом запуске бандла и недоступна для записи.
    """
    if hasattr(sys, "_MEIPASS"):
        # В бандле: папка рядом с .exe / .app
        return Path(sys.executable).parent / "profiles"
    else:
        # В разработке: папка profiles/ в корне проекта
        return Path(__file__).parent.parent / "profiles"