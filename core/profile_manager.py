# core/profile_manager.py
from __future__ import annotations

import json
from pathlib import Path

from core.models import Profile


class ProfileManager:
    """
    Отвечает за сохранение и загрузку профилей настроек.

    Профиль по умолчанию хранится в resources/default_profile.json.
    Пользовательские профили — в произвольных .json файлах (выбирает пользователь).
    """

    # Путь к дефолтному профилю относительно корня проекта
    _DEFAULT_PROFILE_PATH = Path(__file__).parent.parent / "resources" / "default_profile.json"

    def load_default(self) -> Profile:
        """
        Загружает встроенный профиль по умолчанию из resources/.
        Если файл не найден — возвращает жёстко закодированный fallback.
        """
        if self._DEFAULT_PROFILE_PATH.exists():
            return self.load(self._DEFAULT_PROFILE_PATH)
        # Fallback: минимальный профиль, если файл ресурсов отсутствует
        return Profile()

    def load(self, path: Path) -> Profile:
        """
        Загружает профиль из .json файла.

        Raises:
            FileNotFoundError: если файл не существует.
            ValueError:        если файл содержит некорректный JSON.
        """
        if not path.exists():
            raise FileNotFoundError(f"Файл профиля не найден: {path}")

        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Некорректный JSON в файле профиля: {e}") from e

        return Profile.from_dict(data)

    def save(self, profile: Profile, path: Path) -> None:
        """
        Сохраняет профиль в .json файл.

        Создаёт родительские директории при необходимости.

        Raises:
            OSError: при проблемах с записью (нет прав, нет места на диске).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        data = profile.to_dict()
        text = json.dumps(data, ensure_ascii=False, indent=2)
        path.write_text(text, encoding="utf-8")

    def build_profile_from_ui(
        self,
        *,
        profile_name: str,
        max_file_size_kb: int,
        whitelist_text: str,
        blacklist_text: str,
        extensions_text: str,
        output_format: str,
        remove_empty_lines: bool,
        include_file_stats: bool,
    ) -> Profile:
        """
        Фабричный метод: создаёт объект Profile из сырых строк GUI.
        Вызывается из MainWindow перед запуском GenerateWorker.

        Args:
            whitelist_text:   Содержимое QPlainTextEdit белого списка (каждая строка — правило).
            blacklist_text:   Аналогично для чёрного списка.
            extensions_text:  Строка расширений (разделитель — запятая, пробел или перенос строки).
        """
        from core.models import OutputFormat

        def parse_lines(text: str) -> list[str]:
            """Разбивает текст на строки, убирает пустые и пробелы."""
            return [
                line.strip()
                for line in text.replace(",", "\n").splitlines()
                if line.strip()
            ]

        def normalize_extensions(text: str) -> list[str]:
            """Нормализует расширения: добавляет точку если нет, приводит к нижнему регистру."""
            result = []
            for ext in parse_lines(text):
                ext = ext.lower()
                if not ext.startswith("."):
                    ext = f".{ext}"
                result.append(ext)
            return result

        try:
            fmt = OutputFormat(output_format)
        except ValueError:
            fmt = OutputFormat.MARKDOWN

        return Profile(
            profile_name        = profile_name or "Unnamed",
            max_file_size_kb    = max(1, max_file_size_kb),
            whitelist           = parse_lines(whitelist_text),
            blacklist           = parse_lines(blacklist_text),
            ignored_extensions  = normalize_extensions(extensions_text),
            output_format       = fmt,
            remove_empty_lines  = remove_empty_lines,
            include_file_stats  = include_file_stats,
        )