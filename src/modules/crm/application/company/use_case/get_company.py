from src.modules.crm.application.company.dto import CompanyDTO, company_dto
from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class GetCompanyUseCase:
    """Возвращает одну tenant-scoped компанию."""

    def __init__(self, repository: CompanyRepositoryProtocol):
        self.repository = repository

    async def __call__(self, query: GetCompanyQuery) -> CompanyDTO:
        """Читает aggregate и преобразует его в DTO."""
        return company_dto(await self.repository.get(query.tenant_id, query.company_id))


__all__ = ["GetCompanyUseCase"]
