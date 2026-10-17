from src.modules.shared.domain.value_object.entity_id import EntityIdVO
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.files.domain.bucket.aggregate import Bucket
from src.modules.files.domain.error import StorageNotFoundError
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.files.infrastructure.bucket.persistence.mapper import BucketMapper


class SqlAlchemyBucketRepository:
    """Сохраняет агрегат на сессии внешнего tenant UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию с заранее привязанной схемой tenant."""
        self._session = session

    async def get(self, identifier: EntityIdVO) -> Bucket:
        """Загружает зарегистрированный агрегат текущего tenant."""
        row = await self._session.get(BucketModel, identifier.uuid)
        if row is None:
            raise StorageNotFoundError("Storage record was not found.")
        return BucketMapper.to_domain(row)

    async def add(self, aggregate: Bucket) -> None:
        """Добавляет представление агрегата без commit."""
        self._session.add(BucketModel(**BucketMapper.to_insert_values(aggregate)))
        await self._session.flush()

    async def save(self, aggregate: Bucket) -> None:
        """Сохраняет состояние доменного агрегата без commit."""
        await self._session.execute(
            sa.update(BucketModel)
            .where(BucketModel.id == aggregate.id.uuid)
            .values(**BucketMapper.to_update_values(aggregate))
        )

    async def get_system(self, provider_id: EntityIdVO) -> Bucket | None:
        """Находит единственный зарегистрированный бакет подключения."""
        row = await self._session.scalar(
            sa.select(BucketModel).where(BucketModel.provider_id == provider_id.uuid)
        )
        return BucketMapper.to_domain(row) if row is not None else None

    async def list_all(self) -> tuple[Bucket, ...]:
        """Загружает контейнеры для подготовки или очистки tenant-хранилища."""
        rows = await self._session.scalars(
            sa.select(BucketModel).order_by(BucketModel.id)
        )
        return tuple(BucketMapper.to_domain(row) for row in rows)
