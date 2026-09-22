from src.modules.crm.application.company.dto import CompanyPageDTO
from src.modules.crm.application.company.query import (
    CompanyQueryRepositoryProtocol,
    ListCompaniesQuery,
)


class ListCompaniesUseCase:
    """Возвращает найденную страницу компаний."""

    def __init__(self, repository: CompanyQueryRepositoryProtocol):
        self.repository = repository

    async def __call__(self, query: ListCompaniesQuery) -> CompanyPageDTO:
        """Передаёт типизированный запрос в query repository."""
        return await self.repository.list(query)


__all__ = ["ListCompaniesUseCase"]
