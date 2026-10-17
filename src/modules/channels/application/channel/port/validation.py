from typing import Protocol

from src.modules.channels.application.channel.port.registry import ChannelDefinition


class ConnectionValidatorPort(Protocol):
    """Проверяет настройки по опубликованной конфигурации платформы."""

    def validate(self, definition: ChannelDefinition, settings: dict[str, str]) -> None:
        """Отклоняет неверные настройки через безопасные ошибки полей."""
        ...
