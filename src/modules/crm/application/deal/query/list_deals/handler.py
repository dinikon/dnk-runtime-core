from src.modules.crm.application.deal.query.list_deals.query import ListDealsQuery
from src.modules.crm.application.deal.query.list_deals.dto import (
    ListDealsResultDTO,
    DealListItemDTO,
)
from src.modules.crm.application.deal.port.query_repository import (
    DealQueryRepositoryProtocol,
)
from src.modules.crm.application.deal.port.basket import DealBasketPort
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.sales_error import SalesNotFoundError, SalesError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ListDealsHandler:
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

    async def execute(self, query: ListDealsQuery) -> ListDealsResultDTO:
        """Читает проекции без восстановления владельца."""
        if (
            query.offset < 0
            or not 1 <= query.limit <= 100
            or len(query.search) > 255
            or query.sort not in ("updated", "title")
        ):
            raise SalesError("Некорректные параметры списка.")
        rows, total = await self._repository.list(
            funnel_id=query.funnel_id,
            stage_id=query.stage_id,
            search=query.search,
            converted=query.converted,
            offset=query.offset,
            limit=query.limit,
            sort=query.sort,
        )
        summaries = await self._basket.summaries(tuple(r.id for r in rows))
        return ListDealsResultDTO(
            tuple(DealListItemDTO(r, summaries[r.id]) for r in rows),
            total,
            query.offset,
            query.limit,
        )
