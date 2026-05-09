from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.modules.schema_registry.application.config.field.command import (
    AddCustomFieldCommand,
    CustomFieldInput,
    DeleteCustomFieldCommand,
)
from src.modules.schema_registry.application.config.field.dto import CustomFieldDTO
from src.modules.schema_registry.application.config.field.repository import (
    SchemaConfigFieldRepositoryProtocol,
)
from src.modules.schema_registry.application.config.object.command import (
    CreateCustomObjectCommand,
    DeleteCustomObjectCommand,
)
from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO
from src.modules.schema_registry.application.config.object.query import (
    CustomObjectByIdQuery,
    ListCustomObjectsQuery,
)
from src.modules.schema_registry.application.config.object.repository import (
    SchemaConfigRepositoryProtocol,
)
from src.modules.schema_registry.domain.error import (
    FieldNotFoundError,
    InvalidFieldOperationError,
    InvalidObjectOperationError,
    ObjectNameAlreadyExistsError,
    ObjectNotFoundError,
    UnsupportedSchemaChangeError,
)
from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    CreateIndexOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropTableOperation,
)
from src.modules.schema_registry.application.migration.plan import MigrationPlan
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.schema_naming_strategy import (
    SchemaNamingStrategy,
)
from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.naming import (
    normalize_custom_object_names,
)
from src.modules.schema_registry.domain.object.repository import (
    ObjectRepositoryProtocol,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.shared import ClockPort, EntityIdVO


@dataclass(frozen=True, slots=True)
class _SystemFieldSpec:
    """Внутреннее описание системного поля custom-object таблицы."""

    field_name: str
    type: str
    label: str
    description: str
    default_value: str


_SYSTEM_FIELDS = (
    _SystemFieldSpec(
        field_name="id",
        type="uuid",
        label="ID",
        description="Record identifier.",
        default_value="gen_random_uuid()",
    ),
    _SystemFieldSpec(
        field_name="created_at",
        type="datetime",
        label="Created At",
        description="Record creation timestamp.",
        default_value="CURRENT_TIMESTAMP",
    ),
    _SystemFieldSpec(
        field_name="updated_at",
        type="datetime",
        label="Updated At",
        description="Record update timestamp.",
        default_value="CURRENT_TIMESTAMP",
    ),
)


class SchemaConfigRepository(
    SchemaConfigRepositoryProtocol,
    SchemaConfigFieldRepositoryProtocol,
):
    """Config adapter over schema_registry metadata and PostgreSQL DDL."""

    def __init__(
        self,
        *,
        object_repository: ObjectRepositoryProtocol,
        data_source_service: DataSourceService,
        tenant_schema_executor: TenantSchemaExecutorPort,
        postgres_field_canonicalizer: PostgresFieldCanonicalizer,
        field_type_catalog: FieldTypeCatalog,
        clock: ClockPort,
        object_id_provider: Callable[[], RuntimeObjectIdVO],
        field_id_provider: Callable[[], RuntimeFieldIdVO],
    ) -> None:
        """Инициализирует adapter текущей UoW-сессией через переданные порты."""
        self._object_repository = object_repository
        self._data_source_service = data_source_service
        self._tenant_schema_executor = tenant_schema_executor
        self._postgres_field_canonicalizer = postgres_field_canonicalizer
        self._field_type_catalog = field_type_catalog
        self._clock = clock
        self._object_id_provider = object_id_provider
        self._field_id_provider = field_id_provider

    async def list_objects(
        self, query: ListCustomObjectsQuery
    ) -> list[CustomObjectDTO]:
        """Возвращает список runtime objects tenant для config API."""
        objects = await self._object_repository.list_by_tenant_id(
            tenant_id=query.tenant_id
        )
        return [self._to_object_dto(object_entity) for object_entity in objects]

    async def describe_object(self, query: CustomObjectByIdQuery) -> CustomObjectDTO:
        """Возвращает config-схему runtime object tenant."""
        object_entity = await self._get_required_object(
            tenant_id=query.tenant_id,
            object_id=query.object_id,
        )
        return self._to_object_dto(object_entity)

    async def create_object(
        self,
        command: CreateCustomObjectCommand,
    ) -> CustomObjectDTO:
        """Создает custom object metadata и физическую runtime-таблицу."""
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=command.tenant_id,
        )
        singular_name, plural_name = normalize_custom_object_names(
            singular_name=command.singular_name,
            plural_name=command.plural_name,
        )
        object_name = ObjectNameVO(
            singular=singular_name,
            plural=plural_name,
        )
        await self._ensure_object_names_available(
            tenant_id=command.tenant_id,
            object_name=object_name,
        )

        now = self._clock.now()
        object_entity = ObjectEntity.create(
            id_=self._object_id_provider(),
            tenant_id=command.tenant_id,
            data_source_id=datasource.id,
            now=now,
            object_name=object_name,
            object_label=ObjectLabelVO(
                singular=command.singular_label,
                plural=command.plural_label,
            ),
            description=command.description,
            kind=ObjectKind.CUSTOM,
        )

        for system_field in _SYSTEM_FIELDS:
            object_entity.add_field(
                field_id=self._field_id_provider(),
                now=now,
                field_name=system_field.field_name,
                field_type=self._field_type_catalog.from_seed_type(system_field.type),
                label=system_field.label,
                description=system_field.description,
                is_nullable=False,
                default_value=system_field.default_value,
                kind=FieldKind.SYSTEM,
            )
        for field_input in command.fields:
            self._append_custom_field(
                object_entity=object_entity,
                field_input=field_input,
                now=now,
                allow_required_without_default=True,
            )

        plan = MigrationPlan()
        plan.add(
            CreateTableOperation(
                schema_name=datasource.schema_name.value,
                table_name=object_entity.object_name.plural,
            )
        )
        for field_entity in object_entity.fields:
            plan.add(
                self._build_add_column_operation(
                    schema_name=datasource.schema_name.value,
                    table_name=object_entity.object_name.plural,
                    field_entity=field_entity,
                )
            )
        plan.add(
            CreateIndexOperation(
                schema_name=datasource.schema_name.value,
                table_name=object_entity.object_name.plural,
                index_name=self._id_index_name(object_entity),
                columns=("id",),
                is_unique=True,
            )
        )
        await self._tenant_schema_executor.execute(plan=plan)
        await self._object_repository.save(object_entity)
        return self._to_object_dto(object_entity)

    async def delete_object(self, command: DeleteCustomObjectCommand) -> None:
        """Hard-delete custom object table and metadata."""
        object_entity = await self._get_required_object(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        self._ensure_object_can_be_deleted(object_entity)
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=command.tenant_id,
        )
        plan = MigrationPlan()
        plan.add_destructive(
            DropTableOperation(
                schema_name=datasource.schema_name.value,
                table_name=object_entity.object_name.plural,
            )
        )
        await self._tenant_schema_executor.execute(plan=plan)

        objects = await self._object_repository.list_by_tenant_id(
            tenant_id=command.tenant_id
        )
        remaining = [item for item in objects if item.id.uuid != object_entity.id.uuid]
        await self._object_repository.reconcile_for_tenant(
            tenant_id=command.tenant_id,
            objects=remaining,
        )

    async def add_field(self, command: AddCustomFieldCommand) -> CustomObjectDTO:
        """Добавляет custom field и физическую колонку."""
        object_entity = await self._get_required_object(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        self._ensure_object_can_accept_custom_fields(object_entity)
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=command.tenant_id,
        )
        now = self._clock.now()
        field_entity = self._append_custom_field(
            object_entity=object_entity,
            field_input=command.field,
            now=now,
            allow_required_without_default=False,
        )
        plan = MigrationPlan()
        plan.add(
            self._build_add_column_operation(
                schema_name=datasource.schema_name.value,
                table_name=object_entity.object_name.plural,
                field_entity=field_entity,
            )
        )
        await self._tenant_schema_executor.execute(plan=plan)
        await self._object_repository.save(object_entity)
        return self._to_object_dto(object_entity)

    async def delete_field(self, command: DeleteCustomFieldCommand) -> CustomObjectDTO:
        """Удаляет custom field и физическую колонку."""
        object_entity = await self._get_required_object(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        self._ensure_object_can_accept_custom_fields(object_entity)
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=command.tenant_id,
        )
        field_entity = self._get_required_field(
            object_entity=object_entity,
            field_id=command.field_id,
        )
        if not field_entity.can_delete():
            raise InvalidFieldOperationError(
                f"Field '{field_entity.field_name.value}' cannot be deleted."
            )

        plan = MigrationPlan()
        plan.add_destructive(
            DropColumnOperation(
                schema_name=datasource.schema_name.value,
                table_name=object_entity.object_name.plural,
                column_name=field_entity.field_name.value,
            )
        )
        await self._tenant_schema_executor.execute(plan=plan)
        object_entity.remove_field(field_id=command.field_id, now=self._clock.now())
        await self._object_repository.save(object_entity)
        return self._to_object_dto(object_entity)

    async def _get_required_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> ObjectEntity:
        object_entity = await self._object_repository.get_by_id(object_id=object_id)
        if object_entity is None or object_entity.tenant_id != tenant_id:
            raise ObjectNotFoundError(f"Runtime object '{object_id}' was not found.")
        return object_entity

    @staticmethod
    def _ensure_object_can_be_deleted(object_entity: ObjectEntity) -> None:
        if object_entity.can_delete():
            return
        raise InvalidObjectOperationError(
            f"Object '{object_entity.object_name.plural}' cannot be deleted."
        )

    @staticmethod
    def _ensure_object_can_accept_custom_fields(object_entity: ObjectEntity) -> None:
        if object_entity.can_add_custom_fields():
            return
        raise InvalidObjectOperationError(
            f"Object '{object_entity.object_name.plural}' cannot be extended with custom fields."
        )

    async def _ensure_object_names_available(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: ObjectNameVO,
    ) -> None:
        singular_existing = (
            await self._object_repository.get_by_tenant_and_singular_name(
                tenant_id=tenant_id,
                singular_name=object_name.singular,
            )
        )
        plural_existing = await self._object_repository.get_by_tenant_and_plural_name(
            tenant_id=tenant_id,
            plural_name=object_name.plural,
        )
        if singular_existing is not None or plural_existing is not None:
            raise ObjectNameAlreadyExistsError(
                "Custom object singular_name or plural_name already exists."
            )

    def _append_custom_field(
        self,
        *,
        object_entity: ObjectEntity,
        field_input: CustomFieldInput,
        now,
        allow_required_without_default: bool,
    ) -> FieldEntity:
        if (
            not allow_required_without_default
            and not field_input.is_nullable
            and field_input.default_value is None
        ):
            raise UnsupportedSchemaChangeError(
                "Adding required field without default is unsafe for existing object."
            )
        return object_entity.add_field(
            field_id=self._field_id_provider(),
            now=now,
            field_name=field_input.field_name,
            field_type=self._field_type_catalog.from_seed_type(field_input.type),
            label=field_input.label,
            description=field_input.description,
            is_nullable=field_input.is_nullable,
            default_value=self._normalize_default(field_input.default_value),
            options=field_input.options,
            settings=field_input.settings,
            kind=FieldKind.CUSTOM,
        )

    def _build_add_column_operation(
        self,
        *,
        schema_name: str,
        table_name: str,
        field_entity: FieldEntity,
    ) -> AddColumnOperation:
        sql_preset = self._postgres_field_canonicalizer.sql_preset_from_field_type(
            field_entity.field_type
        )
        return AddColumnOperation(
            schema_name=schema_name,
            table_name=table_name,
            column_name=field_entity.field_name.value,
            sql_preset=sql_preset,
            is_nullable=field_entity.is_nullable,
            default_value=self._postgres_field_canonicalizer.normalize_seed_default(
                raw_default=field_entity.default_value,
                sql_preset=sql_preset,
            ),
        )

    @staticmethod
    def _get_required_field(
        *,
        object_entity: ObjectEntity,
        field_id: RuntimeFieldIdVO,
    ) -> FieldEntity:
        for field_entity in object_entity.fields:
            if field_entity.id == field_id:
                return field_entity
        raise FieldNotFoundError(f"Runtime object field '{field_id}' was not found.")

    @staticmethod
    def _normalize_default(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _id_index_name(object_entity: ObjectEntity) -> str:
        base_name = f"{object_entity.object_name.plural}_id_uq"
        if len(base_name) <= 63:
            return SchemaNamingStrategy.validate_identifier(
                base_name,
                title="Custom object id index name",
            )
        suffix = object_entity.id.uuid.hex[:8]
        return SchemaNamingStrategy.validate_identifier(
            f"{object_entity.object_name.plural[:49]}_{suffix}_id_uq",
            title="Custom object id index name",
        )

    @staticmethod
    def _to_object_dto(object_entity: ObjectEntity) -> CustomObjectDTO:
        return CustomObjectDTO(
            id=object_entity.id.uuid,
            created_at=object_entity.created_at,
            updated_at=object_entity.updated_at,
            singular_name=object_entity.object_name.singular,
            plural_name=object_entity.object_name.plural,
            singular_label=object_entity.object_label.singular,
            plural_label=object_entity.object_label.plural,
            description=object_entity.description,
            kind=object_entity.kind.value,
            fields=tuple(
                SchemaConfigRepository._to_field_dto(field_entity)
                for field_entity in object_entity.fields
                if field_entity.kind != FieldKind.SYSTEM
            ),
        )

    @staticmethod
    def _to_field_dto(field_entity: FieldEntity) -> CustomFieldDTO:
        return CustomFieldDTO(
            id=field_entity.id.uuid,
            field_name=field_entity.field_name.value,
            label=field_entity.label.value,
            description=field_entity.description,
            type=field_entity.field_type.code.value,
            is_nullable=field_entity.is_nullable,
            default_value=field_entity.default_value,
            options=dict(field_entity.options),
            kind=field_entity.kind.value,
        )


__all__ = ["SchemaConfigRepository"]
