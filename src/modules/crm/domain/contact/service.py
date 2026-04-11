from src.modules.shared import EntityIdVO
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactCommandRepositoryProtocol
from src.modules.shared.kernel.time.ports import ClockPort


class ContactService:
    def __init__(
        self,
        *,
        command_repository: ContactCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._command_repository = command_repository
        self._clock = clock

    async def create_contact(
        self,
        *,
        contact_id: EntityIdVO,
        last_name: str,
        first_name: str | None = None,
        middle_name: str | None = None,
    ) -> ContactEntity:
        now = self._clock.now()
        contact = ContactEntity.create(
            id_=contact_id,
            now=now,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )

        return await self._command_repository.save(contact=contact)

    async def get_contact(self, *, contact_id: EntityIdVO) -> ContactEntity:
        contact = await self._command_repository.load(contact_id=contact_id)
        if contact is None:
            raise ContactNotFoundError(str(contact_id))

        return contact

    async def rename_contact(
        self,
        *,
        contact_id: EntityIdVO,
        last_name: str,
        first_name: str | None = None,
        middle_name: str | None = None,
    ) -> ContactEntity:
        now = self._clock.now()
        contact = await self.get_contact(contact_id=contact_id)

        contact.rename(
            now=now,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )

        return await self._command_repository.save(contact=contact)

    async def delete_contact(self, *, contact_id: EntityIdVO) -> None:
        await self.get_contact(contact_id=contact_id)

        await self._command_repository.delete(contact_id=contact_id)
