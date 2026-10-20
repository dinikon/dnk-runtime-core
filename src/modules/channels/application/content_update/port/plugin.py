from typing import Protocol
from src.modules.channels.application.content_update.plugin_contract import (
    InspectContentUpdateInputDTO,
    InspectContentUpdateOutcomeDTO,
    SendContentUpdateInputDTO,
    SendContentUpdateOutcomeDTO,
)


class ContentUpdatePlugin(Protocol):
    """Описывает проверку и ограниченную запись контента без native типов площадки."""

    async def inspect(
        self, request: InspectContentUpdateInputDTO
    ) -> InspectContentUpdateOutcomeDTO:
        """Читает существующую карточку и проверяет возможность обновления обоих полей."""
        ...

    async def send(
        self, request: SendContentUpdateInputDTO
    ) -> SendContentUpdateOutcomeDTO:
        """Проверяет исходные тексты и изменяет только разрешённый контент."""
        ...
