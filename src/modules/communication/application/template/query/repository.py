from typing import Protocol

from src.modules.communication.application.template.dto import MessageTemplateDTO
from src.modules.shared import EntityIdVO


class MessageTemplateQueryRepositoryProtocol(Protocol):
    """Порт query-чтения message templates."""

    async def list_templates(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[MessageTemplateDTO]:
        """Возвращает DTO шаблонов tenant."""
        ...


__all__ = ["MessageTemplateQueryRepositoryProtocol"]
