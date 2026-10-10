from src.modules.shared.domain.value_object.entity_id import EntityIdVO
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.files.domain.storage_provider.aggregate import StorageProvider
from src.modules.files.domain.error import StorageNotFoundError
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel,
)
from src.modules.files.infrastructure.storage_provider.persistence.mapper import (
    StorageProviderMapper,
)


class SqlAlchemyStorageProviderRepository:
    """Сохраняет агрегат на сессии внешнего tenant UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию с заранее привязанной схемой tenant."""
        self._session = session

    async def get(self, identifier: EntityIdVO) -> StorageProvider:
        """Загружает зарегистрированный агрегат текущего tenant."""
        row = await self._session.get(StorageProviderModel, identifier.uuid)
        if row is None:
            raise StorageNotFoundError("Storage record was not found.")
        return StorageProviderMapper.to_domain(row)

    async def add(self, aggregate: StorageProvider) -> None:
        """Добавляет представление агрегата без commit."""
        self._session.add(
            StorageProviderModel(**StorageProviderMapper.to_insert_values(aggregate))
        )
        await self._session.flush()

    async def save(self, aggregate: StorageProvider) -> None:
        """Сохраняет состояние доменного агрегата без commit."""
        await self._session.execute(
            sa.update(StorageProviderModel)
            .where(StorageProviderModel.id == aggregate.id.uuid)
            .values(**StorageProviderMapper.to_update_values(aggregate))
        )

    async def get_system(
        self, *, for_registration: bool = False
    ) -> StorageProvider | None:
        """Сериализует регистрацию подключения в текущей tenant-транзакции."""
        if for_registration and self._session.bind.dialect.name == "postgresql":
            await self._session.execute(
                sa.text(
                    "SELECT pg_advisory_xact_lock(hashtextextended(:namespace, 0))"
                ),
                {
                    "namespace": str(
                        (await self._session.connection())
                        .sync_connection.get_execution_options()
                        .get("schema_translate_map", {})
                        .get("tenant", "tenant")
                    )
                    + ":files-system"
                },
            )
        row = await self._session.scalar(
            sa.select(StorageProviderModel).where(
                StorageProviderModel.is_system.is_(True)
            )
        )
        return StorageProviderMapper.to_domain(row) if row is not None else None
