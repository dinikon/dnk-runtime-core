from src.modules.shared.domain.value_object.entity_id import EntityIdVO
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.domain.stored_file.status import StoredFileStatus
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

    async def get_for_update(self, identifier: EntityIdVO) -> StoredFile:
        """Блокирует запись и обновляет ранее загруженное ORM-представление."""
        row = await self._session.scalar(
            sa.select(StoredFileModel)
            .where(StoredFileModel.id == identifier.uuid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise FileNotFoundError("Storage record was not found.")
        return StoredFileMapper.to_domain(row)

    async def remove(self, aggregate: StoredFile) -> None:
        """Удаляет подтверждённый файл, защищаясь от устаревшей purge job."""
        aggregate.ensure_purged()
        result = await self._session.execute(
            sa.delete(StoredFileModel).where(
                StoredFileModel.id == aggregate.id.uuid,
                StoredFileModel.status == StoredFileStatus.PURGING,
                StoredFileModel.purge_job_id == aggregate.purge_job_id.uuid,
            )
        )
        if result.rowcount == 0:
            existing = await self._session.scalar(
                sa.select(StoredFileModel.id).where(
                    StoredFileModel.id == aggregate.id.uuid
                )
            )
            if existing is not None:
                raise FileStateConflictError("Purge job is no longer current.")

    async def save(self, aggregate: StoredFile) -> None:
        """Сохраняет состояние доменного агрегата без commit."""
        await self._session.execute(
            sa.update(StoredFileModel)
            .where(StoredFileModel.id == aggregate.id.uuid)
            .values(**StoredFileMapper.to_update_values(aggregate))
        )
