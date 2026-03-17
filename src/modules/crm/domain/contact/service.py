from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.repository import (
    ContactCommandRepositoryProtocol,
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO
from src.modules.shared.kernel.time.ports import ClockPort


class ContactNotFoundError(Exception):
    pass


class ContactService:
    def __init__(
        self,
        *,
        query_repository: ContactQueryRepositoryProtocol,
        command_repository: ContactCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._query_repository = query_repository
        self._command_repository = command_repository
        self._clock = clock

    async def create_contact(
        self,
        *,
        contact_id: ContactIdVO,
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

        return await self._command_repository.save(contact)

    async def get_contact(
        self,
        *,
        contact_id: ContactIdVO,
    ) -> ContactEntity:
        contact = await self._query_repository.get_by_id(
            contact_id=contact_id,
        )
        if contact is None:
            raise ContactNotFoundError(f"Contact {contact_id} not found")

        return contact

    async def list_contacts(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ContactEntity]:
        return await self._query_repository.list(
            limit=limit,
            offset=offset,
        )

    async def rename_contact(
        self,
        *,
        contact_id: ContactIdVO,
        last_name: str,
        first_name: str | None = None,
        middle_name: str | None = None,
    ) -> ContactEntity:
        now = self._clock.now()
        contact = await self._query_repository.get_by_id(
            contact_id=contact_id,
        )
        if contact is None:
            raise ContactNotFoundError(f"Contact {contact_id} not found")

        contact.rename(
            now=now,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )

        return await self._command_repository.save(contact)

    async def delete_contact(self, *, contact_id: ContactIdVO) -> None:
        contact = await self._query_repository.get_by_id(contact_id=contact_id)
        if contact is None:
            raise ContactNotFoundError(f"Contact {contact_id} not found")

        await self._command_repository.delete(contact_id=contact_id)
