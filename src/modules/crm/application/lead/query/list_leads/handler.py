from src.modules.crm.application.lead.query.list_leads.query import ListLeadsQuery
from src.modules.crm.application.lead.query.list_leads.dto import (
    ListLeadsResultDTO,
    LeadListItemDTO,
)
from src.modules.crm.application.lead.port.query_repository import (
    LeadQueryRepositoryProtocol,
)
from src.modules.crm.application.lead.port.basket import LeadBasketPort
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.sales_error import SalesNotFoundError, SalesError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ListLeadsHandler:
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

    async def execute(self, query: ListLeadsQuery) -> ListLeadsResultDTO:
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
        return ListLeadsResultDTO(
            tuple(LeadListItemDTO(r, summaries[r.id]) for r in rows),
            total,
            query.offset,
            query.limit,
        )
