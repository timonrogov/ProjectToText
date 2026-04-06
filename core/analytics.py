# core/analytics.py
from __future__ import annotations

import tiktoken

from core.models import GenerationResult


class AnalyticsEngine:
    """
    Считает токены и обогащает GenerationResult статистикой.

    tiktoken инициализируется один раз (это медленная операция ~500 мс
    при первом вызове) и переиспользуется.
    """

    # cl100k_base — стандартный кодек для GPT-3.5 / GPT-4 / большинства LLM
    _ENCODING_NAME = "cl100k_base"

    def __init__(self):
        # Lazy initialization — создаём кодировщик только при первом вызове
        self._encoder: tiktoken.Encoding | None = None

    def _get_encoder(self) -> tiktoken.Encoding:
        if self._encoder is None:
            self._encoder = tiktoken.get_encoding(self._ENCODING_NAME)
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """Подсчитывает количество токенов в тексте."""
        encoder = self._get_encoder()
        # disallowed_special=() отключает проверку на спец. токены,
        # кодируя их как обычный текст
        return len(encoder.encode(text, disallowed_special=()))

    def enrich(self, result: GenerationResult) -> GenerationResult:
        """
        Заполняет поле token_count в GenerationResult.
        Возвращает тот же объект (мутирует его) для удобства цепочки вызовов.
        """
        result.token_count = self.count_tokens(result.text)
        return result

    def get_token_level(self, count: int) -> str:
        """
        Возвращает уровень заполнения контекстного окна.
        Используется GUI для цветовой индикации.

        Returns:
            "green"  — до 32 000 токенов (безопасно)
            "yellow" — до 128 000 токенов (предупреждение)
            "red"    — свыше 128 000 токенов (превышение для большинства моделей)
        """
        if count <= 32_000:
            return "green"
        elif count <= 128_000:
            return "yellow"
        return "red"

    def format_token_label(self, count: int) -> str:
        """Форматирует число токенов для отображения в статус-баре."""
        if count >= 1_000_000:
            return f"~{count / 1_000_000:.1f}M токенов"
        elif count >= 1_000:
            return f"~{count // 1_000}K токенов"
        return f"~{count} токенов"