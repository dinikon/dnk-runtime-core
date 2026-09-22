from src.modules.crm.application.company.command import UpdateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDTO, company_dto
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateCompanyUseCase:
    """Обновляет название tenant-scoped компании."""

    def __init__(self, repository: CompanyRepositoryProtocol, clock: ClockPort):
        self.repository = repository
        self.clock = clock

    async def __call__(self, command: UpdateCompanyCommand) -> CompanyDTO:
        """Блокирует aggregate и сохраняет только реальное изменение."""
        company = await self.repository.get(
            command.tenant_id, command.company_id, for_update=True
        )
        changed = company.update(
            actor_id=command.actor_id,
            now=self.clock.now(),
            name=command.name,
        )
        if changed:
            await self.repository.save(command.tenant_id, company)
        return company_dto(company)


__all__ = ["UpdateCompanyUseCase"]
