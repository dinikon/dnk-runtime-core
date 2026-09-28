from src.modules.crm.application.links.company_contacts import CompanyContactsService
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.command import CreateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDetailsDTO
from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.application.company.use_case.get_company import GetCompanyUseCase
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
        read: GetCompanyUseCase,
        links: CompanyContactsService,
    ):
        self.repository = repository
        self.contact_points = contact_points
        self.clock = clock
        self.read = read
        self.links = links

    async def __call__(self, command: CreateCompanyCommand) -> CompanyDetailsDTO:
        """Валидирует aggregate и сохраняет его через repository."""
        requested = command.contact_ids or ()
        contacts = await self.links.lock_contacts(
            command.tenant_id, requested=requested, expected=()
        )
        company = Company.create(
            company_id=command.company_id,
            actor_id=command.actor_id,
            now=self.clock.now(),
            name=command.name,
        )
        await self.repository.add(command.tenant_id, company)
        await self.links.apply(
            command.tenant_id,
            company.id,
            command.actor_id,
            requested=requested,
            expected=(),
            contacts=contacts,
        )
        record_id = EntityIdVO.from_value(company.id.uuid)
        await self.contact_points.sync(
            command.tenant_id,
            command.actor_id,
            "crm.company",
            record_id,
            command.phones,
            command.emails,
        )
        return await self.read(GetCompanyQuery(command.tenant_id, company.id))


__all__ = ["CreateCompanyUseCase"]
