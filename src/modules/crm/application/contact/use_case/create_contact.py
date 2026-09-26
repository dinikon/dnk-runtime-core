from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.command import CreateContactCommand
from src.modules.crm.application.contact.dto import ContactDTO, contact_dto
from src.modules.crm.domain.contact.entity import Contact
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class CreateContactUseCase:
    """Создаёт tenant-scoped CRM-контакт."""

    def __init__(
        self,
        repository: ContactRepositoryProtocol,
        clock: ClockPort,
        contact_points: ContactPointsPort,
    ):
        self.repository = repository
        self.contact_points = contact_points
        self.clock = clock

    async def __call__(self, command: CreateContactCommand) -> ContactDTO:
        """Валидирует aggregate и сохраняет его через repository."""
        contact = Contact.create(
            contact_id=command.contact_id,
            actor_id=command.actor_id,
            now=self.clock.now(),
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
        )
        await self.repository.add(command.tenant_id, contact)
        record_id = EntityIdVO.from_value(contact.id.uuid)
        await self.contact_points.sync(
            command.tenant_id,
            command.actor_id,
            "crm.contact",
            record_id,
            command.phones,
            command.emails,
        )
        points = (
            await self.contact_points.get_many(
                command.tenant_id, "crm.contact", (record_id,)
            )
        )[record_id]
        return replace(contact_dto(contact), phones=points.phones, emails=points.emails)


__all__ = ["CreateContactUseCase"]
