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
class GetLeadResultDTO:
    """Конкретный результат GetLead."""

    record: LeadReadRowDTO
    basket: OwnerBasketProjection
    points: ContactPointsDTO
