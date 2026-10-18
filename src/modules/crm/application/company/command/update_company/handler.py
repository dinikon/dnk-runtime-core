from src.modules.crm.application.company.command.update_company.command import (
    UpdateCompanyCommand,
)
from src.modules.crm.application.company.command.update_company.dto import (
    UpdateCompanyResultDTO,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateCompanyHandler:
    """Обновляет заблокированный агрегат без управления транзакцией."""

    def __init__(self, repository: CompanyRepositoryProtocol, clock: ClockPort) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: UpdateCompanyCommand) -> UpdateCompanyResultDTO:
        company = await self._repository.get_for_update(command.company_id)
        if company is None:
            raise CompanyNotFoundError("Company not found.")
        changed = company.update(
            legal_name=command.legal_name,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        if changed:
            await self._repository.save(company)
        return UpdateCompanyResultDTO(
            id=company.id.uuid,
            legal_name=company.legal_name.value,
            created_at=company.created_at,
            updated_at=company.updated_at,
            created_by=company.created_by.uuid,
            updated_by=company.updated_by.uuid,
        )
