from dataclasses import dataclass
from datetime import datetime
from typing import Any
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO


@dataclass(slots=True, frozen=True)
class UpdateSettingsCommand:
    """Входные данные действия update_settings."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    price_list_id: PriceListIdVO
    title: str
    source_url: str | None
    source_format: str
    source_preset: str | None
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]
    cron_expression: str
    timezone: str
    new_item_policy: str
    missing_item_policy: str
    missing_threshold: int


__all__ = ["UpdateSettingsCommand"]
