from src.modules.crm.application.company.port.stock_owner_usage import (
    CompanyStockOwnerUsagePort,
)
from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyHandler:
    """Удаляет компанию после проверки владения складскими документами."""

    def __init__(
        self,
        repository: CompanyRepositoryProtocol,
        points: ContactPointsPort,
        stock_owners: CompanyStockOwnerUsagePort,
    ) -> None:
        """Принимает порты общей транзакции текущего tenant."""
        self._repository = repository
        self._points = points
        self._stock_owners = stock_owners

    async def execute(self, command: DeleteCompanyCommand) -> None:
        """Блокирует компанию и проверяет использование до удаления контактных данных."""
        company = await self._repository.get_for_update(command.company_id)
        if company is None:
            raise CompanyNotFoundError("Company not found.")
        company.ensure_can_delete(
            used_by_stock_documents=await self._stock_owners.is_used(company.id.uuid),
        )
        await self._points.remove(command.tenant_id, command.company_id)
        await self._repository.delete(company)
