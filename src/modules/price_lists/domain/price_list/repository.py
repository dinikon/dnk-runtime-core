from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO


class PriceListRepository(Protocol):
    """Порт сохранения tenant-scoped aggregate прайса."""

    async def get(
        self,
        tenant_id: EntityIdVO,
        price_list_id: PriceListIdVO,
        *,
        for_update: bool = False,
    ) -> PriceList: ...
    async def add(self, tenant_id: EntityIdVO, price_list: PriceList) -> None: ...
    async def save(self, tenant_id: EntityIdVO, price_list: PriceList) -> None: ...
    async def delete(
        self, tenant_id: EntityIdVO, price_list_id: PriceListIdVO
    ) -> None: ...


__all__ = ["PriceListRepository"]
