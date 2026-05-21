from typing import Protocol

from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError


class GetCompanyUseCaseProtocol(Protocol):
    """Порт use case получения одной компании."""

    async def __call__(self, query: GetCompanyQuery) -> CompanyDTO:
        """Возвращает компанию tenant или поднимает not-found ошибку."""
        ...


class GetCompanyUseCase:
    """Use case чтения одной CRM-компании через query repository."""

    def __init__(self, query_repository: CompanyQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием компаний."""
        self._query_repository = query_repository

    async def __call__(self, query: GetCompanyQuery) -> CompanyDTO:
        """Выполняет query получения компании и проверяет not-found сценарий."""
        company = await self._query_repository.get_by_id(
            tenant_id=query.tenant_id,
            company_id=query.company_id,
        )
        if company is None:
            raise CompanyNotFoundError(str(query.company_id))
        return company
