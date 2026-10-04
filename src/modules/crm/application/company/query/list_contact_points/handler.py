from src.modules.crm.application.contact_point.dto import ContactPointsDTO
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.application.company.port.query_repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.company.query.list_contact_points.query import (
    ListCompanyContactPointsQuery,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError


class ListCompanyContactPointsHandler:
    """Читает расширение только для существующего company."""

    def __init__(
        self, repository: CompanyQueryRepositoryProtocol, points: ContactPointsPort
    ) -> None:
        self._repository = repository
        self._points = points

    async def execute(self, query: ListCompanyContactPointsQuery) -> ContactPointsDTO:
        if await self._repository.get_details(company_id=query.company_id) is None:
            raise CompanyNotFoundError("Company not found.")
        return await self._points.list(query.tenant_id, query.company_id)
