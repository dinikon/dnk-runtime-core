from src.modules.crm.application.company.command import DeleteCompanyCommand
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyUseCase:
    """Физически удаляет tenant-scoped компанию."""

    def __init__(self, repository: CompanyRepositoryProtocol):
        self.repository = repository

    async def __call__(self, command: DeleteCompanyCommand) -> None:
        """Удаляет запись либо поднимает CompanyNotFoundError."""
        await self.repository.delete(command.tenant_id, command.company_id)


__all__ = ["DeleteCompanyUseCase"]
