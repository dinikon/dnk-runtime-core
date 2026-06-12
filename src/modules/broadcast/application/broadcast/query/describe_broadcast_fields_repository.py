from typing import Protocol

from src.modules.broadcast.application.broadcast.dto import (
    BroadcastFieldsDescriptionDTO,
)
from src.modules.shared import EntityIdVO


class BroadcastFieldsDescriptionRepositoryProtocol(Protocol):
    """Порт чтения описания broadcast-модели."""

    async def describe_fields(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> BroadcastFieldsDescriptionDTO:
        """Возвращает описание объекта broadcast и его полей для tenant."""
        ...


__all__ = ["BroadcastFieldsDescriptionRepositoryProtocol"]
