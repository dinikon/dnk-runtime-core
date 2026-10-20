from typing import Protocol
from src.modules.channels.application.plugin_contract import (
    ConnectionSettingsReferencesDTO,
)


class ConnectionReferencesProtocol(Protocol):
    """Проверяет выбранные локали и валюту через владельца справочников."""

    async def validate(self, references: ConnectionSettingsReferencesDTO) -> None:
        """Отклоняет неизвестные или неактивные коды."""
        ...
