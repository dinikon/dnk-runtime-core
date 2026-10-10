from src.modules.shared.domain.value_object.entity_id import EntityIdVO
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.stored_file.persistence.mapper import (
    StoredFileMapper,
)


class SqlAlchemyStoredFileRepository:
    """Сохраняет агрегат на сессии внешнего tenant UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию с заранее привязанной схемой tenant."""
        self._session = session

    async def get(self, identifier: EntityIdVO) -> StoredFile:
        """Загружает зарегистрированный агрегат текущего tenant."""
        row = await self._session.get(StoredFileModel, identifier.uuid)
        if row is None:
            raise FileNotFoundError("Storage record was not found.")
        return StoredFileMapper.to_domain(row)

    async def add(self, aggregate: StoredFile) -> None:
        """Добавляет представление агрегата без commit."""
        self._session.add(
            StoredFileModel(**StoredFileMapper.to_insert_values(aggregate))
        )
        await self._session.flush()

    async def save(self, aggregate: StoredFile) -> None:
        """Сохраняет состояние доменного агрегата без commit."""
        await self._session.execute(
            sa.update(StoredFileModel)
            .where(StoredFileModel.id == aggregate.id.uuid)
            .values(**StoredFileMapper.to_update_values(aggregate))
        )
