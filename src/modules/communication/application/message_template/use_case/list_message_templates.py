from typing import Protocol

from src.modules.communication.application.message_template.dto import (
    MessageTemplateDTO,
)
from src.modules.communication.application.message_template.query import (
    MessageTemplateQueryRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class ListMessageTemplatesUseCaseProtocol(Protocol):
    """Порт use case списка message templates."""

    async def __call__(self, tenant_id: EntityIdVO) -> list[MessageTemplateDTO]:
        """Возвращает список шаблонов tenant."""
        ...


class ListMessageTemplatesUseCase:
    """Use case списка message templates через query repository."""

    def __init__(self, repository: MessageTemplateQueryRepositoryProtocol) -> None:
        """Инициализирует use case query repository шаблонов."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> list[MessageTemplateDTO]:
        """Возвращает DTO шаблонов tenant."""
        return await self._repository.list_templates(tenant_id=tenant_id)


__all__ = [
    "ListMessageTemplatesUseCase",
    "ListMessageTemplatesUseCaseProtocol",
]
