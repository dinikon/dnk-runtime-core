from src.modules.crm.application.links.company_contacts import CompanyContactsService
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.command import UpdateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDetailsDTO
from src.modules.crm.application.company.query import GetCompanyQuery
from src.modules.crm.application.company.use_case.get_company import GetCompanyUseCase
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateCompanyUseCase:
    """Обновляет название tenant-scoped компании."""

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

    async def __call__(self, command: UpdateCompanyCommand) -> CompanyDetailsDTO:
        """Блокирует aggregate и сохраняет только реальное изменение."""
        contacts = None
        if command.contact_ids is not None:
            contacts = await self.links.lock_contacts(
                command.tenant_id,
                requested=command.contact_ids,
                expected=command.expected_contact_ids,
            )
        company = await self.repository.get(
            command.tenant_id, command.company_id, for_update=True
        )
        if contacts is not None:
            await self.links.apply(
                command.tenant_id,
                company.id,
                command.actor_id,
                requested=command.contact_ids,
                expected=command.expected_contact_ids,
                contacts=contacts,
            )
        changed = company.update(
            actor_id=command.actor_id,
            now=self.clock.now(),
            name=command.name,
        )
        if changed:
            await self.repository.save(command.tenant_id, company)
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


__all__ = ["UpdateCompanyUseCase"]
