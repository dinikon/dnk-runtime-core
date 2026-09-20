from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO


@dataclass(slots=True, frozen=True)
class SynchronizePriceListCommand:
    """Данные одного запуска, переданные адаптером очереди."""

    tenant_id: EntityIdVO
    price_list_id: PriceListIdVO
    job_id: EntityIdVO
    revision: int
    trigger: str
    planned_at: datetime
    lock_token: str


__all__ = ["SynchronizePriceListCommand"]
