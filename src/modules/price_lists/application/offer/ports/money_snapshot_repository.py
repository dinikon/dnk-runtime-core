from typing import Protocol
from collections.abc import Sequence
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.application.offer.dto.offer_conversion_dto import (
    OfferConversionDTO,
    OfferMoneySnapshotDTO,
)


class OfferMoneySnapshotRepository(Protocol):
    async def add_many(
        self, *, tenant_id: EntityIdVO, records: Sequence[OfferMoneySnapshotDTO]
    ) -> None: ...
    async def read_many(
        self, *, tenant_id: EntityIdVO, ids: Sequence[UUID], history: bool
    ) -> dict[UUID, OfferConversionDTO]: ...


__all__ = ["OfferMoneySnapshotRepository"]
