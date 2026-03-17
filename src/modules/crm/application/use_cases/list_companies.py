from __future__ import annotations

from src.modules.crm.application.dto import CompanyDTO
from src.modules.crm.application.mappers import company_to_dto
from src.modules.crm.application.queries import ListCompaniesQuery
from src.modules.crm.domain.repositories import CompanyRepositoryProtocol


class ListCompaniesUseCase:
    def __init__(self, *, company_repository: CompanyRepositoryProtocol):
        self._company_repository = company_repository

    async def execute(self, query: ListCompaniesQuery) -> tuple[CompanyDTO, ...]:
        _ = query
        companies = await self._company_repository.list()
        return tuple(company_to_dto(company) for company in companies)


__all__ = ["ListCompaniesUseCase"]
