from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.dto import CompanyDetailsDTO
from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError


class GetCompanyUseCase:
    """Возвращает одну tenant-scoped компанию."""

    def __init__(
        self,
        repository: CompanyQueryRepositoryProtocol,
        contact_points: ContactPointsPort,
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, query: GetCompanyQuery) -> CompanyDetailsDTO:
        """Читает проекцию карточки и обогащает её точками контакта."""
        details = await self.repository.get_details(query.tenant_id, query.company_id)
        if details is None:
            raise CompanyNotFoundError("Company not found.")
        record_id = EntityIdVO.from_value(details.id.uuid)
        points = (
            await self.contact_points.get_many(
                query.tenant_id, "crm.company", (record_id,)
            )
        )[record_id]
        return replace(details, phones=points.phones, emails=points.emails)


__all__ = ["GetCompanyUseCase"]
