from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactCommandRepositoryProtocol
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.kernel.time.ports import ClockPort


class ContactService:
    """Доменный сервис сценариев создания, чтения, обновления и удаления контакта."""

    def __init__(
        self,
        *,
        command_repository: ContactCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис командным репозиторием и clock-портом."""
        self._command_repository = command_repository
        self._clock = clock

    async def create_contact(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
        status: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> ContactEntity:
        """Создает доменную entity контакта и сохраняет ее в command repository."""
        now = self._clock.now()
        contact = ContactEntity.create(
            id_=contact_id,
            now=now,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            status=status,
            tags=tags,
        )

        return await self._command_repository.save(
            tenant_id=tenant_id,
            contact=contact,
        )

    async def get_contact(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactEntity:
        """Возвращает контакт tenant или поднимает ContactNotFoundError."""
        contact = await self._command_repository.load(
            tenant_id=tenant_id,
            contact_id=contact_id,
        )
        if contact is None:
            raise ContactNotFoundError(str(contact_id))

        return contact

    async def rename_contact(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
        status: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> ContactEntity:
        """Загружает контакт, применяет изменения и сохраняет обновленную entity."""
        now = self._clock.now()
        contact = await self.get_contact(
            tenant_id=tenant_id,
            contact_id=contact_id,
        )

        contact.rename(
            now=now,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            status=status,
            tags=tags,
        )

        return await self._command_repository.save(
            tenant_id=tenant_id,
            contact=contact,
        )

    async def delete_contact(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> None:
        """Проверяет существование контакта и удаляет его из repository."""
        await self.get_contact(
            tenant_id=tenant_id,
            contact_id=contact_id,
        )

        await self._command_repository.delete(
            tenant_id=tenant_id,
            contact_id=contact_id,
        )
