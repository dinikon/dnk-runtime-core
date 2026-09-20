from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.application.price_list.dto.price_list_dto import (
    PriceListListItemDTO,
)


class PriceListQueryRepository(Protocol):
    """Порт чтения списка прайсов."""

    async def list(
        self, tenant_id: EntityIdVO, *, scope: str = "current"
    ) -> list[PriceListListItemDTO]: ...


__all__ = ["PriceListQueryRepository"]
