from typing import Protocol

from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.application.company.query import ListCompaniesQuery
from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)


class ListCompaniesUseCaseProtocol(Protocol):
    """Порт use case получения списка компаний."""

    async def __call__(self, query: ListCompaniesQuery) -> list[CompanyDTO]:
        """Возвращает страницу компаний tenant."""
        ...


class ListCompaniesUseCase:
    """Use case чтения списка CRM-компаний через query repository."""

    def __init__(self, query_repository: CompanyQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием компаний."""
        self._query_repository = query_repository

    async def __call__(self, query: ListCompaniesQuery) -> list[CompanyDTO]:
        """Выполняет query списка компаний."""
        return await self._query_repository.list(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
        )
