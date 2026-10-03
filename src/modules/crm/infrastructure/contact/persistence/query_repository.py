from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.contact.persistence.query_mapper import (
    ContactQueryMapper,
)
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel


class SqlAlchemyContactQueryRepository:
    """Читает проекцию контакта одним SELECT в схеме текущего вызова."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию UoW с уже выбранной tenant-схемой."""
        self._session = session

    @staticmethod
    def _details_select():
        """Одна проекция для чтения карточки и списка."""
        return select(
            ContactModel.id.label("id"),
            ContactModel.first_name.label("first_name"),
            ContactModel.last_name.label("last_name"),
            ContactModel.middle_name.label("middle_name"),
            ContactModel.created_at.label("created_at"),
            ContactModel.updated_at.label("updated_at"),
            ContactModel.created_by.label("created_by"),
            ContactModel.updated_by.label("updated_by"),
        )

    async def get_details(
        self,
        *,
        contact_id: ContactIdVO,
    ) -> ContactDetailsDTO | None:
        """Возвращает сохранённые поля без блокировки и загрузки агрегата."""
        result = await self._session.execute(
            self._details_select().where(ContactModel.id == contact_id.uuid)
        )
        row = result.mappings().one_or_none()
        return None if row is None else ContactQueryMapper.to_details(row)

    async def list_details(self) -> list[ContactDetailsDTO]:
        """Читает все проекции tenant с устойчивой сортировкой."""
        result = await self._session.execute(
            self._details_select().order_by(ContactModel.created_at, ContactModel.id)
        )
        return [ContactQueryMapper.to_details(row) for row in result.mappings().all()]
