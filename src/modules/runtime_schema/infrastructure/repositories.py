from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.domain.entities import (
    DataSource,
    FieldMetadata,
    ObjectMetadata,
)
from src.modules.runtime_schema.domain.repositories import (
    DataSourceRepositoryProtocol,
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.infrastructure.mappers import (
    data_source_model_to_entity,
    data_source_to_model,
    field_metadata_model_to_entity,
    field_metadata_to_model,
    object_metadata_model_to_entity,
    object_metadata_to_model,
)
from src.modules.runtime_schema.infrastructure.persistence import (
    RuntimeDataSourceMetadataModel,
    RuntimeFieldMetadataModel,
    RuntimeObjectMetadataModel,
)


class SqlAlchemyDataSourceRepository(DataSourceRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, data_source: DataSource) -> None:
        self._session.add(data_source_to_model(data_source))
        await self._session.flush()

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        model = await self._session.scalar(
            select(RuntimeDataSourceMetadataModel).where(
                RuntimeDataSourceMetadataModel.id == str(data_source_id)
            )
        )
        if model is None:
            return None
        return data_source_model_to_entity(model)

    async def list_by_tenant_id(self, tenant_id: UUID) -> tuple[DataSource, ...]:
        rows = await self._session.scalars(
            select(RuntimeDataSourceMetadataModel)
            .where(RuntimeDataSourceMetadataModel.tenant_id == str(tenant_id))
            .order_by(RuntimeDataSourceMetadataModel.created_at)
        )
        return tuple(data_source_model_to_entity(item) for item in rows)

    async def delete_by_id(self, data_source_id: UUID) -> bool:
        model = await self._session.scalar(
            select(RuntimeDataSourceMetadataModel).where(
                RuntimeDataSourceMetadataModel.id == str(data_source_id)
            )
        )
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True


class SqlAlchemyObjectMetadataRepository(ObjectMetadataRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, object_metadata: ObjectMetadata) -> None:
        self._session.add(object_metadata_to_model(object_metadata))
        await self._session.flush()

    async def get_by_id(self, object_metadata_id: UUID) -> ObjectMetadata | None:
        model = await self._session.scalar(
            select(RuntimeObjectMetadataModel).where(
                RuntimeObjectMetadataModel.id == str(object_metadata_id)
            )
        )
        if model is None:
            return None
        return object_metadata_model_to_entity(model)

    async def get_by_name(
        self,
        *,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None:
        model = await self._session.scalar(
            select(RuntimeObjectMetadataModel)
            .where(RuntimeObjectMetadataModel.tenant_id == str(tenant_id))
            .where(RuntimeObjectMetadataModel.name_singular == name_singular)
        )
        if model is None:
            return None
        return object_metadata_model_to_entity(model)

    async def list_by_tenant_id(
        self,
        tenant_id: UUID,
    ) -> tuple[ObjectMetadata, ...]:
        rows = await self._session.scalars(
            select(RuntimeObjectMetadataModel)
            .where(RuntimeObjectMetadataModel.tenant_id == str(tenant_id))
            .order_by(RuntimeObjectMetadataModel.created_at)
        )
        return tuple(object_metadata_model_to_entity(item) for item in rows)


class SqlAlchemyFieldMetadataRepository(FieldMetadataRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, field_metadata: FieldMetadata) -> None:
        self._session.add(field_metadata_to_model(field_metadata))
        await self._session.flush()

    async def deactivate(self, field_metadata: FieldMetadata) -> None:
        model = await self._session.scalar(
            select(RuntimeFieldMetadataModel).where(
                RuntimeFieldMetadataModel.id == str(field_metadata.id)
            )
        )
        if model is None:
            return

        model.updated_at = field_metadata.updated_at
        model.is_active = field_metadata.is_active
        await self._session.flush()

    async def get_by_id(self, field_metadata_id: UUID) -> FieldMetadata | None:
        model = await self._session.scalar(
            select(RuntimeFieldMetadataModel).where(
                RuntimeFieldMetadataModel.id == str(field_metadata_id)
            )
        )
        if model is None:
            return None
        return field_metadata_model_to_entity(model)

    async def get_by_name(
        self,
        *,
        object_metadata_id: UUID,
        name: str,
    ) -> FieldMetadata | None:
        model = await self._session.scalar(
            select(RuntimeFieldMetadataModel)
            .where(
                RuntimeFieldMetadataModel.object_metadata_id == str(object_metadata_id)
            )
            .where(RuntimeFieldMetadataModel.name == name)
        )
        if model is None:
            return None
        return field_metadata_model_to_entity(model)

    async def list_by_object_metadata_id(
        self,
        object_metadata_id: UUID,
    ) -> tuple[FieldMetadata, ...]:
        rows = await self._session.scalars(
            select(RuntimeFieldMetadataModel)
            .where(
                RuntimeFieldMetadataModel.object_metadata_id == str(object_metadata_id)
            )
            .order_by(RuntimeFieldMetadataModel.created_at)
        )
        return tuple(field_metadata_model_to_entity(item) for item in rows)

    async def delete_by_id(self, field_metadata_id: UUID) -> bool:
        model = await self._session.scalar(
            select(RuntimeFieldMetadataModel).where(
                RuntimeFieldMetadataModel.id == str(field_metadata_id)
            )
        )
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True


class SqlAlchemyRuntimeSchemaRepository:
    def __init__(self, session: AsyncSession):
        self.data_sources = SqlAlchemyDataSourceRepository(session)
        self.objects = SqlAlchemyObjectMetadataRepository(session)
        self.fields = SqlAlchemyFieldMetadataRepository(session)


__all__ = [
    "SqlAlchemyDataSourceRepository",
    "SqlAlchemyFieldMetadataRepository",
    "SqlAlchemyObjectMetadataRepository",
    "SqlAlchemyRuntimeSchemaRepository",
]
