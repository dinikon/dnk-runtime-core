from dataclasses import dataclass
from datetime import datetime
from typing import Any
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO


@dataclass(slots=True, frozen=True)
class PriceListDTO:
    """Публичные данные прайса без секретного URL и служебного actor."""

    id: PriceListIdVO
    title: str
    status: str
    source_format: str
    source_preset: str | None
    source_url_display: str
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]
    mapping_version: int
    cron_expression: str | None
    timezone: str
    new_item_policy: str
    missing_item_policy: str
    missing_threshold: int
    schedule_revision: int
    created_at: datetime
    updated_at: datetime
    next_sync_at: datetime | None
    last_sync_run_id: SyncRunIdVO | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    archived_at: datetime | None


@dataclass(slots=True, frozen=True)
class PriceListListItemDTO(PriceListDTO):
    """Строка списка прайсов с агрегированными показателями."""

    active_offer_count: int
    last_run_status: str | None


def price_list_dto(entity) -> PriceListDTO:
    """Преобразует aggregate в безопасный application DTO."""
    return PriceListDTO(
        **{name: getattr(entity, name) for name in PriceListDTO.__dataclass_fields__}
    )


__all__ = ["PriceListDTO", "PriceListListItemDTO", "price_list_dto"]
