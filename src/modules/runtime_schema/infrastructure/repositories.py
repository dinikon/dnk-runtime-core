from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import (
    FieldIdVO,
    FieldName,
    FieldTypeVO,
)
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import (
    ObjectIdVO,
    ObjectLabelVO,
    ObjectNameVO,
)
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.contracts import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
    SchemaMigrationJournalRepositoryProtocol,
    SchemaVersionEntry,
    SchemaVersionRepositoryProtocol,
)
from src.modules.runtime_schema.infrastructure.ddl_models import MigrationJournalEntry
from src.modules.runtime_schema.infrastructure.field_serialization import (
    deserialize_field_default,
    deserialize_field_options,
    deserialize_field_settings,
    serialize_field_default,
    serialize_field_options,
    serialize_field_settings,
)
from src.modules.runtime_schema.infrastructure.persistence.models import (
    FieldMetadataModel,
    ObjectMetadataModel,
    SchemaMigrationJournalModel,
    SchemaVersionModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyObjectMetadataRepository(ObjectMetadataRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, entity: ObjectMetadataEntity) -> None:
        self._session.add(self._to_model(entity))
        await self._session.flush()

    async def save(self, entity: ObjectMetadataEntity) -> None:
        existing = await self._session.scalar(
            select(ObjectMetadataModel).where(ObjectMetadataModel.id == str(entity.id.value))
        )
        if existing is None:
            await self.add(entity)
            return
        self._apply_to_model(entity=entity, model=existing)
        await self._session.flush()

    async def delete(self, *, object_id: ObjectIdVO) -> None:
        await self._session.execute(
            delete(ObjectMetadataModel).where(ObjectMetadataModel.id == str(object_id.value))
        )
        await self._session.flush()

    async def get_by_id(self, *, object_id: ObjectIdVO) -> ObjectMetadataEntity | None:
        model = await self._session.scalar(
            select(ObjectMetadataModel).where(ObjectMetadataModel.id == str(object_id.value))
        )
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_name(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        object_name_singular: str,
    ) -> ObjectMetadataEntity | None:
        model = await self._session.scalar(
            select(ObjectMetadataModel)
            .where(ObjectMetadataModel.tenant_id == str(tenant_id.value))
            .where(ObjectMetadataModel.data_source_id == str(data_source_id.value))
            .where(ObjectMetadataModel.name_singular == object_name_singular.strip().lower())
            .limit(1)
        )
        if model is None:
            return None
        return self._to_entity(model)

    async def list_by_tenant_data_source(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
    ) -> list[ObjectMetadataEntity]:
        models = (
            await self._session.scalars(
                select(ObjectMetadataModel)
                .where(ObjectMetadataModel.tenant_id == str(tenant_id.value))
                .where(ObjectMetadataModel.data_source_id == str(data_source_id.value))
                .order_by(ObjectMetadataModel.created_at, ObjectMetadataModel.name_singular)
            )
        ).all()
        return [self._to_entity(model) for model in models]

    @staticmethod
    def _to_model(entity: ObjectMetadataEntity) -> ObjectMetadataModel:
        return ObjectMetadataModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            data_source_id=entity.data_source_id.value,
            name_singular=entity.object_name.name_singular,
            name_plural=entity.object_name.name_plural,
            label_singular=entity.object_label.name_singular,
            label_plural=entity.object_label.name_plural,
            description=entity.description,
            icon=entity.icon,
            shortcut=entity.shortcut,
            duplicate_criteria=entity.duplicate_criteria or {},
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _apply_to_model(
        *,
        entity: ObjectMetadataEntity,
        model: ObjectMetadataModel,
    ) -> None:
        model.tenant_id = entity.tenant_id.value
        model.data_source_id = entity.data_source_id.value
        model.name_singular = entity.object_name.name_singular
        model.name_plural = entity.object_name.name_plural
        model.label_singular = entity.object_label.name_singular
        model.label_plural = entity.object_label.name_plural
        model.description = entity.description
        model.icon = entity.icon
        model.shortcut = entity.shortcut
        model.duplicate_criteria = entity.duplicate_criteria or {}
        model.updated_at = entity.updated_at

    @staticmethod
    def _to_entity(model: ObjectMetadataModel) -> ObjectMetadataEntity:
        return ObjectMetadataEntity(
            id=ObjectIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            data_source_id=DataSourceIdVO.from_value(model.data_source_id),
            object_name=ObjectNameVO(
                name_singular=model.name_singular,
                name_plural=model.name_plural,
            ),
            object_label=ObjectLabelVO(
                name_singular=model.label_singular,
                name_plural=model.label_plural,
            ),
            description=model.description,
            icon=model.icon,
            shortcut=model.shortcut,
            duplicate_criteria=model.duplicate_criteria or {},
        )


class SqlAlchemyFieldMetadataRepository(FieldMetadataRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, entity: FieldMetadataEntity) -> None:
        self._session.add(self._to_model(entity))
        await self._session.flush()

    async def save(self, entity: FieldMetadataEntity) -> None:
        existing = await self._session.scalar(
            select(FieldMetadataModel).where(FieldMetadataModel.id == str(entity.id.value))
        )
        if existing is None:
            await self.add(entity)
            return
        self._apply_to_model(entity=entity, model=existing)
        await self._session.flush()

    async def delete(self, *, field_id: FieldIdVO) -> None:
        await self._session.execute(
            delete(FieldMetadataModel).where(FieldMetadataModel.id == str(field_id.value))
        )
        await self._session.flush()

    async def get_by_id(self, *, field_id: FieldIdVO) -> FieldMetadataEntity | None:
        model = await self._session.scalar(
            select(FieldMetadataModel).where(FieldMetadataModel.id == str(field_id.value))
        )
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_object_and_name(
        self,
        *,
        object_id: ObjectIdVO,
        field_name: str,
    ) -> FieldMetadataEntity | None:
        model = await self._session.scalar(
            select(FieldMetadataModel)
            .where(FieldMetadataModel.object_metadata_id == str(object_id.value))
            .where(FieldMetadataModel.field_name == field_name.strip().lower())
            .limit(1)
        )
        if model is None:
            return None
        return self._to_entity(model)

    async def list_by_object(
        self,
        *,
        object_id: ObjectIdVO,
    ) -> list[FieldMetadataEntity]:
        models = (
            await self._session.scalars(
                select(FieldMetadataModel)
                .where(FieldMetadataModel.object_metadata_id == str(object_id.value))
                .order_by(FieldMetadataModel.created_at, FieldMetadataModel.field_name)
            )
        ).all()
        return [self._to_entity(model) for model in models]

    async def list_by_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[FieldMetadataEntity]:
        models = (
            await self._session.scalars(
                select(FieldMetadataModel)
                .where(FieldMetadataModel.tenant_id == str(tenant_id.value))
                .order_by(FieldMetadataModel.created_at, FieldMetadataModel.field_name)
            )
        ).all()
        return [self._to_entity(model) for model in models]

    @staticmethod
    def _to_model(entity: FieldMetadataEntity) -> FieldMetadataModel:
        return FieldMetadataModel(
            id=entity.id.value,
            tenant_id=entity.tenant_id.value,
            object_metadata_id=entity.object_metadata_id.value,
            field_type=entity.field_type.value,
            field_name=entity.field_name.value,
            label=entity.label,
            description=entity.description,
            icon=entity.icon,
            is_unique=entity.is_unique,
            is_index=entity.is_index,
            is_nullable=entity.is_nullable,
            is_searchable=entity.is_searchable,
            options=serialize_field_options(entity.options),
            settings=serialize_field_settings(entity.settings),
            default_value=serialize_field_default(entity.default_value),
            relation_target_object_id=(
                entity.relation_target_object_id.value
                if entity.relation_target_object_id is not None
                else None
            ),
            relation_target_field_id=(
                entity.relation_target_field_id.value
                if entity.relation_target_field_id is not None
                else None
            ),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _apply_to_model(*, entity: FieldMetadataEntity, model: FieldMetadataModel) -> None:
        model.tenant_id = entity.tenant_id.value
        model.object_metadata_id = entity.object_metadata_id.value
        model.field_type = entity.field_type.value
        model.field_name = entity.field_name.value
        model.label = entity.label
        model.description = entity.description
        model.icon = entity.icon
        model.is_unique = entity.is_unique
        model.is_index = entity.is_index
        model.is_nullable = entity.is_nullable
        model.is_searchable = entity.is_searchable
        model.options = serialize_field_options(entity.options)
        model.settings = serialize_field_settings(entity.settings)
        model.default_value = serialize_field_default(entity.default_value)
        model.relation_target_object_id = (
            entity.relation_target_object_id.value
            if entity.relation_target_object_id is not None
            else None
        )
        model.relation_target_field_id = (
            entity.relation_target_field_id.value
            if entity.relation_target_field_id is not None
            else None
        )
        model.updated_at = entity.updated_at

    @staticmethod
    def _to_entity(model: FieldMetadataModel) -> FieldMetadataEntity:
        field_type = FieldTypeVO(model.field_type)
        options = deserialize_field_options(field_type=field_type, payload=model.options)
        settings = deserialize_field_settings(field_type=field_type, payload=model.settings)
        default_value = deserialize_field_default(
            field_type=field_type,
            payload=model.default_value,
        )

        return FieldMetadataEntity(
            id=FieldIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            object_metadata_id=ObjectIdVO.from_value(model.object_metadata_id),
            field_type=field_type,
            field_name=FieldName(model.field_name),
            label=model.label,
            description=model.description,
            icon=model.icon,
            is_unique=model.is_unique,
            is_index=model.is_index,
            is_nullable=model.is_nullable,
            is_searchable=model.is_searchable,
            options=options,
            settings=settings,
            default_value=default_value,
            relation_target_object_id=(
                ObjectIdVO.from_value(model.relation_target_object_id)
                if model.relation_target_object_id is not None
                else None
            ),
            relation_target_field_id=(
                FieldIdVO.from_value(model.relation_target_field_id)
                if model.relation_target_field_id is not None
                else None
            ),
        )


class SqlAlchemySchemaVersionRepository(SchemaVersionRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        schema: str,
    ) -> SchemaVersionEntry | None:
        model = await self._session.scalar(
            select(SchemaVersionModel)
            .where(SchemaVersionModel.tenant_id == str(tenant_id.value))
            .where(SchemaVersionModel.schema == schema)
            .limit(1)
        )
        if model is None:
            return None
        return SchemaVersionEntry(
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            data_source_id=DataSourceIdVO.from_value(model.data_source_id),
            schema=model.schema,
            version=model.version,
            manifest_hash=model.manifest_hash,
            updated_at=model.updated_at,
        )

    async def upsert(self, entry: SchemaVersionEntry) -> None:
        model = await self._session.scalar(
            select(SchemaVersionModel)
            .where(SchemaVersionModel.tenant_id == str(entry.tenant_id.value))
            .where(SchemaVersionModel.schema == entry.schema)
            .limit(1)
        )
        if model is None:
            self._session.add(
                SchemaVersionModel(
                    tenant_id=entry.tenant_id.value,
                    data_source_id=entry.data_source_id.value,
                    schema=entry.schema,
                    version=entry.version,
                    manifest_hash=entry.manifest_hash,
                    updated_at=entry.updated_at,
                )
            )
        else:
            model.data_source_id = entry.data_source_id.value
            model.version = entry.version
            model.manifest_hash = entry.manifest_hash
            model.updated_at = entry.updated_at
        await self._session.flush()


class SqlAlchemySchemaMigrationJournalRepository(
    SchemaMigrationJournalRepositoryProtocol
):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_entries(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        entries: list[MigrationJournalEntry],
    ) -> None:
        for entry in entries:
            self._session.add(
                SchemaMigrationJournalModel(
                    tenant_id=tenant_id.value,
                    data_source_id=data_source_id.value,
                    schema=schema,
                    operation_key=entry.operation_key,
                    operation_sql=entry.operation_sql,
                    status=entry.status,
                    error_message=entry.error_message,
                    created_at=entry.created_at,
                    applied_at=entry.applied_at,
                )
            )
        await self._session.flush()


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "SqlAlchemyFieldMetadataRepository",
    "SqlAlchemyObjectMetadataRepository",
    "SqlAlchemySchemaMigrationJournalRepository",
    "SqlAlchemySchemaVersionRepository",
    "utc_now",
]
