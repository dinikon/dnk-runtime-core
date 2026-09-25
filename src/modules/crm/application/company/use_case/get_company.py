from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.dto import CompanyDTO, company_dto
from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class GetCompanyUseCase:
    """Возвращает одну tenant-scoped компанию."""

    def __init__(
        self, repository: CompanyRepositoryProtocol, contact_points: ContactPointsPort
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, query: GetCompanyQuery) -> CompanyDTO:
        """Читает aggregate и преобразует его в DTO."""
        entity = await self.repository.get(query.tenant_id, query.company_id)
        record_id = EntityIdVO.from_value(entity.id.uuid)
        points = (
            await self.contact_points.get_many(
                query.tenant_id, "crm.company", (record_id,)
            )
        )[record_id]
        return replace(company_dto(entity), phones=points.phones, emails=points.emails)


__all__ = ["GetCompanyUseCase"]
