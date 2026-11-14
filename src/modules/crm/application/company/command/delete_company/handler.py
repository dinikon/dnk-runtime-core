from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.application.counterparty_reference.source_usage import (
    CounterpartySourceUsagePort,
)
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyHandler:
    """Удаляет компанию после проверки внешних источников и собственных связей."""

    def __init__(
        self,
        repository: CompanyRepositoryProtocol,
        points: ContactPointsPort,
        sources: CounterpartySourceUsagePort,
    ) -> None:
        """Принимает порты общей транзакции текущего tenant."""
        self._repository = repository
        self._points = points
        self._sources = sources

    async def execute(self, command: DeleteCompanyCommand) -> None:
        """Блокирует компанию и проверяет использование до удаления контактных данных."""
        company = await self._repository.get_for_update(command.company_id)
        if company is None:
            raise CompanyNotFoundError("Company not found.")
        company.ensure_can_delete(
            used_by_supplier_sources=await self._sources.is_used(
                CounterpartyModelKey.COMPANY, company.id.uuid
            )
        )
        await self._points.remove(command.tenant_id, command.company_id)
        await self._repository.delete(company)
