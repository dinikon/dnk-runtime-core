from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.types import JsonObject

type StockDirection = Literal["read", "write"]
type StockSyncStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


@dataclass(frozen=True, slots=True)
class StockSnapshotVO:
    """Наблюдаемый остаток и фактический владелец количества на площадке."""

    resource_type: str
    external_id: str
    mode: str
    quantity: Decimal | None
    availability: str | None
    backorders: str | None = None

    def __post_init__(self) -> None:
        """Не смешивает неизвестное количество, ноль и ручное наличие."""
        if (
            not isinstance(self.resource_type, str)
            or not self.resource_type
            or not isinstance(self.external_id, str)
            or not self.external_id
            or not isinstance(self.mode, str)
            or self.mode not in {"own", "untracked", "unknown", "not_applicable"}
            or (
                self.quantity is not None
                and (
                    not isinstance(self.quantity, Decimal)
                    or not self.quantity.is_finite()
                )
            )
            or (
                self.backorders is not None
                and (
                    not isinstance(self.backorders, str)
                    or self.backorders not in {"no", "notify", "yes"}
                )
            )
            or (
                self.availability is not None
                and (
                    not isinstance(self.availability, str)
                    or self.availability
                    not in {
                        "in_stock",
                        "out_of_stock",
                        "on_order",
                        "removed",
                        "not_applicable",
                    }
                )
            )
        ):
            raise StockSyncError("stock_snapshot_invalid")

    def to_document(self) -> JsonObject:
        """Сохраняет точное количество строкой."""
        return {
            "resource_type": self.resource_type,
            "external_id": self.external_id,
            "mode": self.mode,
            "quantity": str(self.quantity) if self.quantity is not None else None,
            "availability": self.availability,
            "backorders": self.backorders,
        }


@dataclass(frozen=True, slots=True)
class StockLinkFacts:
    """Только факты принадлежности двух количественных пулов."""

    publication_id: EntityIdVO
    platform_owner_id: EntityIdVO
    catalog_position_id: EntityIdVO
    catalog_owner_id: EntityIdVO
    quantity: int | None
    backorders: str
    platform_target_key: str | None = None


class StockOwnershipPolicy:
    """Запрещает неоднозначное объединение или разложение общего количества."""

    def ensure_exportable(
        self, selected: StockLinkFacts, links: tuple[StockLinkFacts, ...]
    ) -> None:
        """Проверяет всю топологию подключения, включая другие группы связей."""
        if selected.quantity is None:
            raise StockSyncError("stock_tracking_required")
        if (
            selected.platform_target_key is not None
            and len(
                {
                    link.platform_owner_id
                    for link in links
                    if link.platform_target_key == selected.platform_target_key
                }
            )
            > 1
        ):
            raise StockSyncError("stock_ownership_ambiguous")
        # Отрицательное значение Catalog сохраняется; неподдержанный экспорт отклоняется.
        if selected.quantity < 0:
            raise StockSyncError("stock_negative_unsupported")
        if (
            len(
                {
                    v.catalog_owner_id
                    for v in links
                    if v.platform_owner_id == selected.platform_owner_id
                }
            )
            > 1
        ):
            raise StockSyncError("stock_ownership_ambiguous")
        if (
            selected.catalog_position_id != selected.catalog_owner_id
            and len(
                {
                    v.platform_owner_id
                    for v in links
                    if v.catalog_owner_id == selected.catalog_owner_id
                }
            )
            > 1
        ):
            raise StockSyncError("stock_ownership_ambiguous")
