from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.command import CreateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDTO, company_dto
from src.modules.crm.domain.company.entity import Company
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class CreateCompanyUseCase:
    """Создаёт tenant-scoped CRM-компанию."""

    def __init__(
        self,
        repository: CompanyRepositoryProtocol,
        clock: ClockPort,
        contact_points: ContactPointsPort,
    ):
        self.repository = repository
        self.contact_points = contact_points
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
        record_id = EntityIdVO.from_value(company.id.uuid)
        await self.contact_points.sync(
            command.tenant_id,
            command.actor_id,
            "crm.company",
            record_id,
            command.phones,
            command.emails,
        )
        points = (
            await self.contact_points.get_many(
                command.tenant_id, "crm.company", (record_id,)
            )
        )[record_id]
        return replace(company_dto(company), phones=points.phones, emails=points.emails)


__all__ = ["CreateCompanyUseCase"]
