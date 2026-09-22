from src.modules.crm.application.company.command import CreateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDTO, company_dto
from src.modules.crm.domain.company.entity import Company
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class CreateCompanyUseCase:
    """Создаёт tenant-scoped CRM-компанию."""

    def __init__(self, repository: CompanyRepositoryProtocol, clock: ClockPort):
        self.repository = repository
        self.clock = clock

    async def __call__(self, command: CreateCompanyCommand) -> CompanyDTO:
        """Валидирует aggregate и сохраняет его через repository."""
        company = Company.create(
            company_id=command.company_id,
            actor_id=command.actor_id,
            now=self.clock.now(),
            name=command.name,
        )
        await self.repository.add(command.tenant_id, company)
        return company_dto(company)


__all__ = ["CreateCompanyUseCase"]
