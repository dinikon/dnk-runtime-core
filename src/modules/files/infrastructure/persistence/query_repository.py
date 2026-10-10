from uuid import UUID
from src.modules.files.infrastructure.persistence.query_mapper import StorageQueryMapper
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.files.application.port.query_repository import FileContentLocationDTO
from src.modules.files.application.storage_provider.query.list_providers.dto import (
    ProviderListItemDTO,
)
from src.modules.files.application.bucket.query.list_buckets.dto import (
    BucketListItemDTO,
)
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel as Provider,
)
from src.modules.files.infrastructure.persistence.models.bucket import (
    BucketModel as Bucket,
)
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel as File,
)


class SqlAlchemyStorageQueryRepository:
    """Читает tenant-проекции без загрузки domain aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию с привязанной tenant-схемой."""
        self._session = session

    async def providers(self) -> tuple[ProviderListItemDTO, ...]:
        """Возвращает безопасные подключения без конфигурации и credentials."""
        rows = await self._session.execute(
            sa.select(
                Provider.id, Provider.name, Provider.kind, Provider.is_system
            ).order_by(Provider.is_system.desc(), Provider.name, Provider.id)
        )
        return tuple(StorageQueryMapper.to_provider(row) for row in rows.mappings())

    async def buckets(self, provider_id: UUID | None) -> tuple[BucketListItemDTO, ...]:
        """Считает готовые зарегистрированные файлы одним SQL-запросом."""
        stmt = (
            sa.select(
                Bucket.id,
                Bucket.provider_id,
                Bucket.name,
                Bucket.status,
                sa.func.count(File.id).label("files_count"),
                sa.func.coalesce(sa.func.sum(File.size_bytes), 0).label("size_bytes"),
            )
            .outerjoin(
                File,
                sa.and_(
                    File.bucket_id == Bucket.id,
                    File.status == "ready",
                    Bucket.status == "ready",
                ),
            )
            .group_by(Bucket.id)
            .order_by(Bucket.name, Bucket.id)
        )
        if provider_id is not None:
            stmt = stmt.where(Bucket.provider_id == provider_id)
        rows = await self._session.execute(stmt)
        return tuple(StorageQueryMapper.to_bucket(row) for row in rows.mappings())

    async def content_location(
        self, tenant_id: UUID, file_id: UUID
    ) -> FileContentLocationDTO | None:
        """Читает координаты доступного файла, не раскрывая ORM наружу."""
        stmt = (
            sa.select(
                File.object_key,
                File.name,
                File.content_type,
                File.size_bytes,
                Bucket.id.label("bucket_id"),
                Bucket.name.label("bucket_name"),
                Provider.kind,
                Provider.config_ref,
            )
            .join(Bucket, File.bucket_id == Bucket.id)
            .join(Provider, Bucket.provider_id == Provider.id)
            .where(File.id == file_id, File.status == "ready", Bucket.status == "ready")
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()
        if row is None:
            return None
        return StorageQueryMapper.to_content_location(tenant_id, row)

    async def contains_key(self, bucket_id: UUID, key: str) -> bool:
        """Проверяет ключ без построения большого списка файлов в памяти."""
        return bool(
            await self._session.scalar(
                sa.select(
                    sa.exists().where(
                        File.bucket_id == bucket_id, File.object_key == key
                    )
                )
            )
        )
