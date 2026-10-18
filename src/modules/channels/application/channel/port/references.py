from typing import Protocol
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)


class ConnectionReferencesProtocol(Protocol):
    """Проверяет выбранные локали и валюту через владельца справочников."""

    async def validate(self, settings: ConnectionSettingsVO) -> None:
        """Отклоняет неизвестные или неактивные коды."""
        ...
