from typing import Protocol

from src.modules.crm.application.company.command import DeleteCompanyCommand
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyCommandRepositoryProtocol


class DeleteCompanyUseCaseProtocol(Protocol):
    """Порт use case удаления компании."""

    async def __call__(self, command: DeleteCompanyCommand) -> None:
        """Удаляет компанию tenant."""
        ...


class DeleteCompanyUseCase:
    """Use case удаления CRM-компании."""

    def __init__(self, command_repository: CompanyCommandRepositoryProtocol):
        """Инициализирует use case командным репозиторием компаний."""
        self._command_repository = command_repository

    async def __call__(self, command: DeleteCompanyCommand) -> None:
        """Выполняет команду удаления компании."""
        company = await self._command_repository.load(
            tenant_id=command.tenant_id,
            company_id=command.company_id,
        )
        if company is None:
            raise CompanyNotFoundError(str(command.company_id))

        await self._command_repository.delete(
            tenant_id=command.tenant_id,
            company_id=command.company_id,
        )
