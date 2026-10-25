from src.modules.crm.application.lead.query.get_lead.query import GetLeadQuery
from src.modules.crm.application.lead.query.get_lead.dto import GetLeadResultDTO
from src.modules.crm.application.lead.port.query_repository import (
    LeadQueryRepositoryProtocol,
)
from src.modules.crm.application.lead.port.basket import LeadBasketPort
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.sales_error import SalesNotFoundError, SalesError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class GetLeadHandler:
    """Собирает read-модель через собственные и внешние порты."""

    def __init__(
        self,
        repository: LeadQueryRepositoryProtocol,
        basket: LeadBasketPort,
        points: ContactPointsPort,
    ) -> None:
        """Принимает порты чтения без SQL-типов."""
        self._repository = repository
        self._basket = basket
        self._points = points

    async def execute(self, query: GetLeadQuery) -> GetLeadResultDTO:
        """Читает проекции без восстановления владельца."""
        record = await self._repository.get(query.record_id)
        if record is None:
            raise SalesNotFoundError("Карточка не найдена.")
        basket = await self._basket.get(record.id)
        points = await self._points.list(
            EntityIdVO(query.tenant_id), EntityIdVO(record.id)
        )
        return GetLeadResultDTO(record, basket, points)
