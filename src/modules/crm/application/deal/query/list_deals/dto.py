from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from src.modules.crm.application.basket.values import (
    BasketInput,
    OwnerBasketProjection,
    BasketSummaryProjection,
)
from src.modules.crm.application.contact_point.dto import (
    ContactPointDraftDTO,
    ContactPointsDTO,
)
from src.modules.crm.application.deal.port.read_row import DealReadRowDTO


@dataclass(frozen=True, slots=True)
class DealListItemDTO:
    """Строка списка Deal с пакетной денежной сводкой."""

    record: DealReadRowDTO
    basket: BasketSummaryProjection


@dataclass(frozen=True, slots=True)
class ListDealsResultDTO:
    """Конкретный результат ListDeals."""

    items: tuple[DealListItemDTO, ...]
    total: int
    offset: int
    limit: int
