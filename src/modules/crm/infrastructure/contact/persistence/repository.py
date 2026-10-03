from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.contact.aggregate import ContactEntity
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.contact.persistence.mapper import ContactMapper
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel


class SqlAlchemyContactRepository:
    """Сохраняет контакты в tenant-схеме на сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию UoW с уже выбранной tenant-схемой."""
        self._session = session

    async def add(self, contact: ContactEntity) -> None:
        """Добавляет агрегат в схему соединения без commit/rollback."""
        await self._session.execute(
            insert(ContactModel).values(ContactMapper.to_insert_values(contact))
        )

    async def get_for_update(self, contact_id: ContactIdVO) -> ContactEntity | None:
        """Блокирует контакт до завершения общего UoW."""
        result = await self._session.execute(
            select(
                ContactModel.id.label("id"),
                ContactModel.first_name.label("first_name"),
                ContactModel.last_name.label("last_name"),
                ContactModel.middle_name.label("middle_name"),
                ContactModel.created_at.label("created_at"),
                ContactModel.updated_at.label("updated_at"),
                ContactModel.created_by.label("created_by"),
                ContactModel.updated_by.label("updated_by"),
            )
            .where(ContactModel.id == contact_id.uuid)
            .with_for_update()
        )
        row = result.mappings().one_or_none()
        return None if row is None else ContactMapper.to_entity(row)

    async def save(self, contact: ContactEntity) -> None:
        """Записывает проверенное доменом ФИО без завершения транзакции."""
        await self._session.execute(
            update(ContactModel)
            .where(ContactModel.id == contact.id.uuid)
            .values(ContactMapper.to_update_values(contact))
        )

    async def delete(self, contact: ContactEntity) -> None:
        """Физически удаляет запись; внешние ключи обрабатывает БД."""
        await self._session.execute(
            delete(ContactModel).where(ContactModel.id == contact.id.uuid)
        )
