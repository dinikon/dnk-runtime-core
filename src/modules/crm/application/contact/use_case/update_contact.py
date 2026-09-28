from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.command import UpdateContactCommand
from src.modules.crm.application.contact.dto import ContactDetailsDTO
from src.modules.crm.application.contact.query import GetContactQuery
from src.modules.crm.application.contact.use_case.get_contact import GetContactUseCase
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateContactUseCase:
    """Обновляет ФИО tenant-scoped контакта."""

    def __init__(
        self,
        repository: ContactRepositoryProtocol,
        clock: ClockPort,
        contact_points: ContactPointsPort,
        read: GetContactUseCase,
        companies: CompanyRepositoryProtocol,
    ):
        self.repository = repository
        self.contact_points = contact_points
        self.clock = clock
        self.read = read
        self.companies = companies

    async def __call__(self, command: UpdateContactCommand) -> ContactDetailsDTO:
        """Блокирует aggregate и сохраняет только реальное изменение."""
        contact = await self.repository.get(
            command.tenant_id, command.contact_id, for_update=True
        )
        changed = contact.update(
            actor_id=command.actor_id,
            now=self.clock.now(),
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
        )
        if command.company_ids is not None:
            previous = contact.company_ids
            links_changed = contact.replace_companies(
                requested=command.company_ids,
                expected=command.expected_company_ids,
                actor_id=command.actor_id,
                now=self.clock.now(),
            )
            for company_id in sorted(
                previous | contact.company_ids, key=lambda value: value.uuid
            ):
                await self.companies.get(command.tenant_id, company_id, for_share=True)
            changed = changed or links_changed
        if changed:
            await self.repository.save(command.tenant_id, contact)
        record_id = EntityIdVO.from_value(contact.id.uuid)
        await self.contact_points.sync(
            command.tenant_id,
            command.actor_id,
            "crm.contact",
            record_id,
            command.phones,
            command.emails,
        )
        return await self.read(GetContactQuery(command.tenant_id, contact.id))


__all__ = ["UpdateContactUseCase"]
