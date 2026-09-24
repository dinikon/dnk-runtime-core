from typing import Protocol

from src.modules.crm.application.company.dto.company_dto import CompanyPageDTO
from src.modules.crm.application.company.query.list_companies_query import (
    ListCompaniesQuery,
)


class CompanyQueryRepositoryProtocol(Protocol):
    """Порт чтения страницы компаний."""

    async def list(self, query: ListCompaniesQuery) -> CompanyPageDTO: ...


__all__ = ["CompanyQueryRepositoryProtocol"]
