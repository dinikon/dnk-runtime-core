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
from src.modules.crm.application.lead.port.read_row import LeadReadRowDTO


@dataclass(frozen=True, slots=True)
class LeadListItemDTO:
    """Строка списка Lead с пакетной денежной сводкой."""

    record: LeadReadRowDTO
    basket: BasketSummaryProjection


@dataclass(frozen=True, slots=True)
class ListLeadsResultDTO:
    """Конкретный результат ListLeads."""

    items: tuple[LeadListItemDTO, ...]
    total: int
    offset: int
    limit: int
