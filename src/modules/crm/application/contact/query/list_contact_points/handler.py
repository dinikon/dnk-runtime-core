from src.modules.crm.application.contact_point.dto import ContactPointsDTO
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.application.contact.port.query_repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.list_contact_points.query import (
    ListContactContactPointsQuery,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError


class ListContactContactPointsHandler:
    """Читает расширение только для существующего contact."""

    def __init__(
        self, repository: ContactQueryRepositoryProtocol, points: ContactPointsPort
    ) -> None:
        self._repository = repository
        self._points = points

    async def execute(self, query: ListContactContactPointsQuery) -> ContactPointsDTO:
        if await self._repository.get_details(contact_id=query.contact_id) is None:
            raise ContactNotFoundError("Contact not found.")
        return await self._points.list(query.tenant_id, query.contact_id)
