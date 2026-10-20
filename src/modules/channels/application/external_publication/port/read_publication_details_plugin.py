from typing import Protocol
from src.modules.channels.application.plugin_contract import (
    ReadPublicationDetailsInputDTO,
    ReadPublicationDetailsOutcomeDTO,
)


class ReadPublicationDetailsPlugin(Protocol):
    """Получает полное содержимое одной публикации без доступа к хранилищам ядра."""

    async def execute(
        self, request: ReadPublicationDetailsInputDTO
    ) -> ReadPublicationDetailsOutcomeDTO:
        """Читает настроенные локали и галерею либо явно сообщает об ошибке."""
        ...
