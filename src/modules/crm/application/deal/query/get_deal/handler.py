from src.modules.crm.application.deal.query.get_deal.query import GetDealQuery
from src.modules.crm.application.deal.query.get_deal.dto import GetDealResultDTO
from src.modules.crm.application.deal.port.query_repository import (
    DealQueryRepositoryProtocol,
)
from src.modules.crm.application.deal.port.basket import DealBasketPort
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.sales_error import SalesNotFoundError, SalesError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class GetDealHandler:
    """Собирает read-модель через собственные и внешние порты."""

    def __init__(
        self,
        repository: DealQueryRepositoryProtocol,
        basket: DealBasketPort,
        points: ContactPointsPort,
    ) -> None:
        """Принимает порты чтения без SQL-типов."""
        self._repository = repository
        self._basket = basket
        self._points = points

    async def execute(self, query: GetDealQuery) -> GetDealResultDTO:
        """Читает проекции без восстановления владельца."""
        record = await self._repository.get(query.record_id)
        if record is None:
            raise SalesNotFoundError("Карточка не найдена.")
        basket = await self._basket.get(record.id)
        points = await self._points.list(
            EntityIdVO(query.tenant_id), EntityIdVO(record.id)
        )
        return GetDealResultDTO(record, basket, points)
