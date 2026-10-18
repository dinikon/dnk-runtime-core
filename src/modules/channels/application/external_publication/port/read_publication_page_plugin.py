from typing import Protocol
from src.modules.channels.application.plugin_contract import (
    ReadPublicationPageInputDTO,
    ReadPublicationPageOutcomeDTO,
)


class ReadPublicationPagePlugin(Protocol):
    """Читает ограниченную порцию публикаций или следующий поток."""

    async def execute(
        self, request: ReadPublicationPageInputDTO
    ) -> ReadPublicationPageOutcomeDTO:
        """Возвращает типизированный результат одного сетевого шага."""
        ...
