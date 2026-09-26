from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.command import UpdateContactCommand
from src.modules.crm.application.contact.dto import ContactDTO, contact_dto
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateContactUseCase:
    """Обновляет ФИО tenant-scoped контакта."""

    def __init__(
        self,
        repository: ContactRepositoryProtocol,
        clock: ClockPort,
        contact_points: ContactPointsPort,
    ):
        self.repository = repository
        self.contact_points = contact_points
        self.clock = clock

    async def __call__(self, command: UpdateContactCommand) -> ContactDTO:
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
        points = (
            await self.contact_points.get_many(
                command.tenant_id, "crm.contact", (record_id,)
            )
        )[record_id]
        return replace(contact_dto(contact), phones=points.phones, emails=points.emails)


__all__ = ["UpdateContactUseCase"]
