from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.contact.aggregate import ContactEntity
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
