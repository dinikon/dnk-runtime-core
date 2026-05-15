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
from src.modules.schema_registry.application.config.relation.command import (
    CreateRelationCommand,
    DeleteRelationCommand,
)
from src.modules.schema_registry.application.config.relation.dto import RelationDTO
from src.modules.schema_registry.application.config.relation.query import (
    ListObjectRelationsQuery,
)
from src.modules.schema_registry.application.config.relation.repository import (
    SchemaConfigRelationRepositoryProtocol,
)
from src.modules.schema_registry.domain.error import (
    FieldNotFoundError,
    InvalidFieldOperationError,
    InvalidObjectOperationError,
    InvalidRelationOperationError,
    ObjectNameAlreadyExistsError,
    ObjectNotFoundError,
    RelationNotFoundError,
    UnsupportedSchemaChangeError,
)
from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    AddPrimaryKeyOperation,
    CreateIndexOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
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
from src.modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import FieldNameVO
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
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
from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.repository import (
    RelationRepositoryProtocol,
)
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
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
    SchemaConfigRelationRepositoryProtocol,
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
        relation_repository: RelationRepositoryProtocol | None = None,
        tenant_schema_inspector: TenantSchemaInspectorPort | None = None,
        relation_id_provider: Callable[[], RuntimeRelationIdVO] | None = None,
    ) -> None:
        """Инициализирует adapter текущей UoW-сессией через переданные порты."""
        self._object_repository = object_repository
        self._relation_repository = relation_repository
        self._data_source_service = data_source_service
        self._tenant_schema_executor = tenant_schema_executor
        self._tenant_schema_inspector = tenant_schema_inspector
        self._postgres_field_canonicalizer = postgres_field_canonicalizer
        self._field_type_catalog = field_type_catalog
        self._clock = clock
        self._object_id_provider = object_id_provider
        self._field_id_provider = field_id_provider
        self._relation_id_provider = relation_id_provider

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

    async def list_object_relations(
        self,
        query: ListObjectRelationsQuery,
    ) -> list[RelationDTO]:
        """Возвращает relations, где object участвует как source или target."""
        object_entity = await self._get_required_object(
            tenant_id=query.tenant_id,
            object_id=query.object_id,
        )
        relations = await self._relation_repository.list_by_object_id(
            tenant_id=query.tenant_id,
            object_id=object_entity.id,
        )
        objects = await self._object_repository.list_by_tenant_id(
            tenant_id=query.tenant_id,
        )
        return [
            self._to_relation_dto(relation, objects=objects) for relation in relations
        ]

    async def create_relation(
        self,
        command: CreateRelationCommand,
    ) -> RelationDTO:
        """Создает custom relation, сначала применяя физический DDL."""
        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=command.tenant_id,
        )
        relation_input = command.relation
        relation_name = self._validate_identifier(relation_input.name, "Relation name")
        existing = await self._relation_repository.get_by_tenant_and_name(
            tenant_id=command.tenant_id,
            name=relation_name,
        )
        if existing is not None:
            raise InvalidRelationOperationError(
                f"Relation '{relation_name}' already exists."
            )

        relation_type = self._normalize_relation_type(relation_input.relation_type)
        source_object = await self._get_required_object(
            tenant_id=command.tenant_id,
            object_id=relation_input.source_object_id,
        )
        target_object = await self._get_required_object(
            tenant_id=command.tenant_id,
            object_id=relation_input.target_object_id,
        )
        self._ensure_object_can_accept_custom_relation(source_object)
        self._ensure_object_can_accept_custom_relation(target_object)

        if relation_type == RelationTypeEnum.MANY_TO_MANY:
            relation = await self._create_many_to_many_relation(
                tenant_id=command.tenant_id,
                schema_name=datasource.schema_name.value,
                data_source_id=datasource.id,
                relation_name=relation_name,
                source_object=source_object,
                target_object=target_object,
                command=relation_input,
            )
        else:
            relation = await self._create_fk_relation(
                tenant_id=command.tenant_id,
                schema_name=datasource.schema_name.value,
                data_source_id=datasource.id,
                relation_name=relation_name,
                relation_type=relation_type,
                source_object=source_object,
                target_object=target_object,
                command=relation_input,
            )

        objects = await self._object_repository.list_by_tenant_id(
            tenant_id=command.tenant_id,
        )
        return self._to_relation_dto(relation, objects=objects)

    async def delete_relation(self, command: DeleteRelationCommand) -> None:
        """Удаляет custom relation, сначала удаляя physical artifacts."""
        relation = await self._relation_repository.get_by_id(
            relation_id=command.relation_id,
        )
        if relation is None or relation.tenant_id != command.tenant_id:
            raise RelationNotFoundError(
                f"Relation '{command.relation_id}' was not found."
            )
        if relation.kind != "custom":
            raise InvalidRelationOperationError(
                f"Relation '{relation.name}' cannot be deleted because it is not custom."
            )

        datasource = await self._data_source_service.get_required_by_tenant(
            tenant_id=command.tenant_id,
        )
        objects = await self._object_repository.list_by_tenant_id(
            tenant_id=command.tenant_id,
        )
        objects_by_id = {item.id: item for item in objects}
        fields_by_id = {field.id: field for item in objects for field in item.fields}
        plan = MigrationPlan()
        object_to_save: ObjectEntity | None = None

        if relation.relation_type == RelationTypeEnum.MANY_TO_MANY:
            if relation.relation_table_name is None:
                raise InvalidRelationOperationError(
                    f"Relation '{relation.name}' has incomplete M2M metadata."
                )
            has_rows = await self._tenant_schema_inspector.table_has_rows(
                schema_name=datasource.schema_name.value,
                table_name=relation.relation_table_name,
            )
            if has_rows:
                raise InvalidRelationOperationError(
                    f"Relation '{relation.name}' cannot be deleted while relation table has rows."
                )
            plan.add_destructive(
                DropTableOperation(
                    schema_name=datasource.schema_name.value,
                    table_name=relation.relation_table_name,
                )
            )
        else:
            if (
                relation.owning_object_id is None
                or relation.referenced_object_id is None
                or relation.fk_field_id is None
            ):
                raise InvalidRelationOperationError(
                    f"Relation '{relation.name}' has incomplete FK metadata."
                )
            owning_object = objects_by_id[relation.owning_object_id]
            referenced_object = objects_by_id[relation.referenced_object_id]
            fk_field = fields_by_id[relation.fk_field_id]
            has_values = await self._tenant_schema_inspector.column_has_non_null_values(
                schema_name=datasource.schema_name.value,
                table_name=owning_object.object_name.plural,
                column_name=fk_field.field_name.value,
            )
            if has_values:
                raise InvalidRelationOperationError(
                    f"Relation '{relation.name}' cannot be deleted while FK column has non-null values."
                )
            plan.add_destructive(
                DropForeignKeyOperation(
                    schema_name=datasource.schema_name.value,
                    table_name=owning_object.object_name.plural,
                    constraint_name=SchemaNamingStrategy.foreign_key_name(
                        source_table_name=owning_object.object_name.plural,
                        source_column_name=fk_field.field_name.value,
                        target_table_name=referenced_object.object_name.plural,
                    ),
                )
            )
            plan.add_destructive(
                DropIndexOperation(
                    schema_name=datasource.schema_name.value,
                    index_name=self._relation_fk_index_name(
                        relation=relation,
                        table_name=owning_object.object_name.plural,
                        column_name=fk_field.field_name.value,
                    ),
                )
            )
            if fk_field.kind == FieldKind.CUSTOM:
                plan.add_destructive(
                    DropColumnOperation(
                        schema_name=datasource.schema_name.value,
                        table_name=owning_object.object_name.plural,
                        column_name=fk_field.field_name.value,
                    )
                )
                object_to_save = owning_object

        await self._tenant_schema_executor.execute(plan=plan)
        if object_to_save is not None and relation.fk_field_id is not None:
            object_to_save.remove_field(
                field_id=relation.fk_field_id,
                now=self._clock.now(),
            )
            await self._object_repository.save(object_to_save)
        await self._relation_repository.delete(
            tenant_id=command.tenant_id,
            relation_id=command.relation_id,
        )

    async def _create_fk_relation(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_name: str,
        data_source_id,
        relation_name: str,
        relation_type: RelationTypeEnum,
        source_object: ObjectEntity,
        target_object: ObjectEntity,
        command,
    ) -> RelationEntity:
        """Создает FK-based relation и associated FK/index/field DDL."""
        owning_object = await self._resolve_owning_object(
            tenant_id=tenant_id,
            relation_type=relation_type,
            source_object=source_object,
            target_object=target_object,
            owning_object_id=command.owning_object_id,
        )
        referenced_object = await self._resolve_referenced_object(
            tenant_id=tenant_id,
            relation_type=relation_type,
            source_object=source_object,
            target_object=target_object,
            referenced_object_id=command.referenced_object_id,
        )
        self._ensure_object_can_accept_custom_relation(owning_object)
        self._ensure_object_can_accept_custom_relation(referenced_object)

        fk_field_name = self._validate_identifier(
            command.fk_field_name or "",
            "FK field name",
        )
        referenced_field_name = self._validate_identifier(
            command.referenced_field_name or "id",
            "Referenced field name",
        )
        referenced_field = self._find_field_by_name(
            object_entity=referenced_object,
            field_name=referenced_field_name,
        )
        if referenced_field is None:
            raise FieldNotFoundError(
                f"Referenced field '{referenced_field_name}' was not found."
            )
        if referenced_field.field_name.value != "id":
            raise InvalidRelationOperationError(
                "Config-created relations can reference only primary id field in MVP."
            )

        existing_fk_field = self._find_field_by_name(
            object_entity=owning_object,
            field_name=fk_field_name,
        )
        new_fk_field = False
        now = self._clock.now()
        if existing_fk_field is None:
            if command.is_required:
                table_has_rows = await self._tenant_schema_inspector.table_has_rows(
                    schema_name=schema_name,
                    table_name=owning_object.object_name.plural,
                )
                if table_has_rows:
                    raise UnsupportedSchemaChangeError(
                        "Adding required FK on non-empty table is unsafe in MVP."
                    )
            fk_field = FieldEntity.create(
                id_=self._field_id_provider(),
                object_id=owning_object.id,
                now=now,
                field_name=FieldNameVO(fk_field_name),
                field_type=self._field_type_catalog.from_seed_type("reference"),
                label=FieldLabelVO(command.label or fk_field_name),
                description="",
                is_nullable=not command.is_required,
                kind=FieldKind.CUSTOM,
            )
            owning_object.fields.append(fk_field)
            new_fk_field = True
        else:
            fk_field = existing_fk_field
            if fk_field.field_type.code.value != "reference":
                raise InvalidFieldOperationError(
                    f"FK field '{fk_field_name}' must have type 'reference'."
                )
            if fk_field.kind == FieldKind.SYSTEM:
                raise InvalidFieldOperationError(
                    f"FK field '{fk_field_name}' cannot be system field."
                )
            await self._ensure_field_is_not_bound_to_relation(
                tenant_id=tenant_id,
                field=fk_field,
            )

        relation = RelationEntity.create(
            id_=self._relation_id_provider(),
            now=now,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name=relation_name,
            label=command.label,
            relation_type=relation_type,
            source_object_id=source_object.id,
            target_object_id=target_object.id,
            owning_object_id=owning_object.id,
            fk_field_id=fk_field.id,
            referenced_object_id=referenced_object.id,
            referenced_field_id=referenced_field.id,
            source_relation_name=self._relation_source_api_name(
                command.source_relation_name,
                relation_type=relation_type,
                target_object=target_object,
            ),
            target_relation_name=self._relation_target_api_name(
                command.target_relation_name,
                relation_type=relation_type,
                source_object=source_object,
            ),
            relation_table_name=None,
            source_join_column_name=None,
            target_join_column_name=None,
            on_delete=self._normalize_on_delete(command.on_delete),
            is_required=command.is_required,
            is_unique=relation_type == RelationTypeEnum.ONE_TO_ONE,
            kind="custom",
            settings=command.settings,
        )
        await self._ensure_relation_api_names_available(
            tenant_id=tenant_id,
            relation=relation,
        )

        plan = MigrationPlan()
        if new_fk_field:
            plan.add(
                self._build_add_column_operation(
                    schema_name=schema_name,
                    table_name=owning_object.object_name.plural,
                    field_entity=fk_field,
                )
            )
        plan.add(
            CreateIndexOperation(
                schema_name=schema_name,
                table_name=owning_object.object_name.plural,
                index_name=self._relation_fk_index_name(
                    relation=relation,
                    table_name=owning_object.object_name.plural,
                    column_name=fk_field.field_name.value,
                ),
                columns=(fk_field.field_name.value,),
                is_unique=relation.is_unique,
            )
        )
        plan.add(
            AddForeignKeyOperation(
                schema_name=schema_name,
                table_name=owning_object.object_name.plural,
                constraint_name=SchemaNamingStrategy.foreign_key_name(
                    source_table_name=owning_object.object_name.plural,
                    source_column_name=fk_field.field_name.value,
                    target_table_name=referenced_object.object_name.plural,
                ),
                column_name=fk_field.field_name.value,
                target_schema_name=schema_name,
                target_table_name=referenced_object.object_name.plural,
                target_column_name=referenced_field.field_name.value,
                on_delete=relation.on_delete,
            )
        )
        await self._tenant_schema_executor.execute(plan=plan)
        if new_fk_field:
            await self._object_repository.save(owning_object)
        await self._relation_repository.add(relation)
        return relation

    async def _create_many_to_many_relation(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_name: str,
        data_source_id,
        relation_name: str,
        source_object: ObjectEntity,
        target_object: ObjectEntity,
        command,
    ) -> RelationEntity:
        """Создает M2M relation и physical join table."""
        if source_object.id == target_object.id:
            raise InvalidRelationOperationError(
                "Self many_to_many relations are not supported in MVP."
            )
        table_name = self._validate_identifier(
            command.relation_table_name
            or f"{source_object.object_name.plural}_{target_object.object_name.plural}",
            "Relation table name",
        )
        source_column = self._validate_identifier(
            command.source_join_column_name
            or f"{source_object.object_name.singular}_id",
            "Source join column name",
        )
        target_column = self._validate_identifier(
            command.target_join_column_name
            or f"{target_object.object_name.singular}_id",
            "Target join column name",
        )
        if source_column == target_column:
            raise InvalidRelationOperationError("M2M join columns must differ.")
        await self._ensure_relation_table_name_available(
            tenant_id=tenant_id,
            table_name=table_name,
        )

        now = self._clock.now()
        relation = RelationEntity.create(
            id_=self._relation_id_provider(),
            now=now,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name=relation_name,
            label=command.label,
            relation_type=RelationTypeEnum.MANY_TO_MANY,
            source_object_id=source_object.id,
            target_object_id=target_object.id,
            owning_object_id=None,
            fk_field_id=None,
            referenced_object_id=None,
            referenced_field_id=None,
            source_relation_name=(
                command.source_relation_name or target_object.object_name.plural
            ),
            target_relation_name=(
                command.target_relation_name or source_object.object_name.plural
            ),
            relation_table_name=table_name,
            source_join_column_name=source_column,
            target_join_column_name=target_column,
            on_delete=self._normalize_on_delete(command.on_delete),
            is_required=command.is_required,
            is_unique=False,
            kind="custom",
            settings=command.settings,
        )
        await self._ensure_relation_api_names_available(
            tenant_id=tenant_id,
            relation=relation,
        )

        plan = MigrationPlan()
        plan.add(CreateTableOperation(schema_name=schema_name, table_name=table_name))
        plan.add(
            AddColumnOperation(
                schema_name=schema_name,
                table_name=table_name,
                column_name="id",
                sql_preset=SqlTypePresetEnum.UUID,
                is_nullable=False,
                default_value="gen_random_uuid()",
            )
        )
        plan.add(
            AddColumnOperation(
                schema_name=schema_name,
                table_name=table_name,
                column_name="created_at",
                sql_preset=SqlTypePresetEnum.TIMESTAMP,
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
            )
        )
        for column_name in (source_column, target_column):
            plan.add(
                AddColumnOperation(
                    schema_name=schema_name,
                    table_name=table_name,
                    column_name=column_name,
                    sql_preset=SqlTypePresetEnum.UUID,
                    is_nullable=False,
                )
            )
        plan.add(
            AddPrimaryKeyOperation(
                schema_name=schema_name,
                table_name=table_name,
                constraint_name=SchemaNamingStrategy.primary_key_name(
                    table_name=table_name,
                ),
                columns=("id",),
            )
        )
        plan.add(
            CreateIndexOperation(
                schema_name=schema_name,
                table_name=table_name,
                index_name=SchemaNamingStrategy.many_to_many_unique_index_name(
                    table_name=table_name,
                    source_column_name=source_column,
                    target_column_name=target_column,
                ),
                columns=(source_column, target_column),
                is_unique=True,
            )
        )
        for column_name in (source_column, target_column):
            plan.add(
                CreateIndexOperation(
                    schema_name=schema_name,
                    table_name=table_name,
                    index_name=SchemaNamingStrategy.foreign_key_index_name(
                        table_name=table_name,
                        column_name=column_name,
                    ),
                    columns=(column_name,),
                    is_unique=False,
                )
            )
        for column_name, target in (
            (source_column, source_object),
            (target_column, target_object),
        ):
            plan.add(
                AddForeignKeyOperation(
                    schema_name=schema_name,
                    table_name=table_name,
                    constraint_name=SchemaNamingStrategy.foreign_key_name(
                        source_table_name=table_name,
                        source_column_name=column_name,
                        target_table_name=target.object_name.plural,
                    ),
                    column_name=column_name,
                    target_schema_name=schema_name,
                    target_table_name=target.object_name.plural,
                    target_column_name="id",
                    on_delete=relation.on_delete,
                )
            )
        await self._tenant_schema_executor.execute(plan=plan)
        await self._relation_repository.add(relation)
        return relation

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

    async def _resolve_owning_object(
        self,
        *,
        tenant_id: EntityIdVO,
        relation_type: RelationTypeEnum,
        source_object: ObjectEntity,
        target_object: ObjectEntity,
        owning_object_id: RuntimeObjectIdVO | None,
    ) -> ObjectEntity:
        expected = (
            target_object
            if relation_type == RelationTypeEnum.ONE_TO_MANY
            else source_object
        )
        if owning_object_id is None:
            return expected
        owning_object = await self._get_required_object(
            tenant_id=tenant_id,
            object_id=owning_object_id,
        )
        if owning_object.id != expected.id:
            raise InvalidRelationOperationError(
                f"Invalid owning_object '{owning_object.object_name.plural}' "
                f"for relation type '{relation_type.value}'."
            )
        return owning_object

    async def _resolve_referenced_object(
        self,
        *,
        tenant_id: EntityIdVO,
        relation_type: RelationTypeEnum,
        source_object: ObjectEntity,
        target_object: ObjectEntity,
        referenced_object_id: RuntimeObjectIdVO | None,
    ) -> ObjectEntity:
        expected = (
            source_object
            if relation_type == RelationTypeEnum.ONE_TO_MANY
            else target_object
        )
        if referenced_object_id is None:
            return expected
        referenced_object = await self._get_required_object(
            tenant_id=tenant_id,
            object_id=referenced_object_id,
        )
        if referenced_object.id != expected.id:
            raise InvalidRelationOperationError(
                f"Invalid referenced_object '{referenced_object.object_name.plural}' "
                f"for relation type '{relation_type.value}'."
            )
        return referenced_object

    async def _ensure_field_is_not_bound_to_relation(
        self,
        *,
        tenant_id: EntityIdVO,
        field: FieldEntity,
    ) -> None:
        relations = await self._relation_repository.list_by_tenant_id(
            tenant_id=tenant_id,
        )
        if any(relation.fk_field_id == field.id for relation in relations):
            raise InvalidRelationOperationError(
                f"Field '{field.field_name.value}' is already bound to relation."
            )

    async def _ensure_relation_api_names_available(
        self,
        *,
        tenant_id: EntityIdVO,
        relation: RelationEntity,
    ) -> None:
        relations = await self._relation_repository.list_by_tenant_id(
            tenant_id=tenant_id,
        )
        for existing in relations:
            if (
                existing.source_object_id == relation.source_object_id
                and existing.source_relation_name == relation.source_relation_name
            ):
                raise InvalidRelationOperationError(
                    f"Duplicate source_relation_name '{relation.source_relation_name}'."
                )
            if (
                existing.target_object_id == relation.target_object_id
                and existing.target_relation_name == relation.target_relation_name
            ):
                raise InvalidRelationOperationError(
                    f"Duplicate target_relation_name '{relation.target_relation_name}'."
                )

    async def _ensure_relation_table_name_available(
        self,
        *,
        tenant_id: EntityIdVO,
        table_name: str,
    ) -> None:
        objects = await self._object_repository.list_by_tenant_id(tenant_id=tenant_id)
        object_table_names = {item.object_name.plural for item in objects}
        if table_name in object_table_names:
            raise InvalidRelationOperationError(
                f"Relation table '{table_name}' conflicts with object table."
            )
        relations = await self._relation_repository.list_by_tenant_id(
            tenant_id=tenant_id,
        )
        relation_table_names = {
            relation.relation_table_name
            for relation in relations
            if relation.relation_table_name is not None
        }
        if table_name in relation_table_names:
            raise InvalidRelationOperationError(
                f"Relation table '{table_name}' already exists."
            )

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

    @staticmethod
    def _ensure_object_can_accept_custom_relation(object_entity: ObjectEntity) -> None:
        if object_entity.kind in {ObjectKind.STANDARD, ObjectKind.CUSTOM}:
            return
        raise InvalidRelationOperationError(
            f"Object '{object_entity.object_name.plural}' cannot be used in custom relation."
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
    def _relation_source_api_name(
        value: str | None,
        *,
        relation_type: RelationTypeEnum,
        target_object: ObjectEntity,
    ) -> str:
        if value:
            return value.strip()
        if relation_type == RelationTypeEnum.ONE_TO_MANY:
            return target_object.object_name.plural
        return target_object.object_name.singular

    @staticmethod
    def _relation_target_api_name(
        value: str | None,
        *,
        relation_type: RelationTypeEnum,
        source_object: ObjectEntity,
    ) -> str:
        if value:
            return value.strip()
        if relation_type == RelationTypeEnum.ONE_TO_MANY:
            return source_object.object_name.singular
        return source_object.object_name.plural

    @staticmethod
    def _relation_fk_index_name(
        *,
        relation: RelationEntity,
        table_name: str,
        column_name: str,
    ) -> str:
        if relation.is_unique:
            return SchemaNamingStrategy.one_to_one_unique_index_name(
                table_name=table_name,
                column_name=column_name,
            )
        return SchemaNamingStrategy.foreign_key_index_name(
            table_name=table_name,
            column_name=column_name,
        )

    @staticmethod
    def _find_field_by_name(
        *,
        object_entity: ObjectEntity,
        field_name: str,
    ) -> FieldEntity | None:
        normalized = field_name.strip()
        for field_entity in object_entity.fields:
            if field_entity.field_name.value == normalized:
                return field_entity
        return None

    @staticmethod
    def _validate_identifier(value: str, title: str) -> str:
        return SchemaNamingStrategy.validate_identifier(value, title=title)

    @staticmethod
    def _normalize_relation_type(value: str) -> RelationTypeEnum:
        try:
            return RelationTypeEnum(value.strip().lower())
        except ValueError as exc:
            raise InvalidRelationOperationError(
                f"Unsupported relation_type '{value}'."
            ) from exc

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        mapping = {
            "restrict": "restrict",
            "cascade": "cascade",
            "set null": "set_null",
            "set_null": "set_null",
            "no action": "no_action",
            "no_action": "no_action",
        }
        try:
            return mapping[value.strip().lower()]
        except KeyError as exc:
            raise InvalidRelationOperationError(
                f"Unsupported relation on_delete '{value}'."
            ) from exc

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

    @staticmethod
    def _to_relation_dto(
        relation: RelationEntity,
        *,
        objects: list[ObjectEntity],
    ) -> RelationDTO:
        objects_by_id = {item.id: item for item in objects}
        fields_by_id = {field.id: field for item in objects for field in item.fields}
        source_object = objects_by_id[relation.source_object_id]
        target_object = objects_by_id[relation.target_object_id]
        owning_object = (
            None
            if relation.owning_object_id is None
            else objects_by_id[relation.owning_object_id]
        )
        referenced_object = (
            None
            if relation.referenced_object_id is None
            else objects_by_id[relation.referenced_object_id]
        )
        fk_field = (
            None if relation.fk_field_id is None else fields_by_id[relation.fk_field_id]
        )
        referenced_field = (
            None
            if relation.referenced_field_id is None
            else fields_by_id[relation.referenced_field_id]
        )
        return RelationDTO(
            id=relation.id.uuid,
            created_at=relation.created_at,
            updated_at=relation.updated_at,
            name=relation.name,
            label=relation.label,
            relation_type=relation.relation_type.value,
            source_object_id=relation.source_object_id.uuid,
            target_object_id=relation.target_object_id.uuid,
            source_object=source_object.object_name.plural,
            target_object=target_object.object_name.plural,
            source_relation_name=relation.source_relation_name,
            target_relation_name=relation.target_relation_name,
            owning_object_id=(
                relation.owning_object_id.uuid
                if relation.owning_object_id is not None
                else None
            ),
            owning_object=(
                owning_object.object_name.plural if owning_object is not None else None
            ),
            fk_field_id=(
                relation.fk_field_id.uuid if relation.fk_field_id is not None else None
            ),
            fk_field=fk_field.field_name.value if fk_field is not None else None,
            referenced_object_id=(
                relation.referenced_object_id.uuid
                if relation.referenced_object_id is not None
                else None
            ),
            referenced_object=(
                referenced_object.object_name.plural
                if referenced_object is not None
                else None
            ),
            referenced_field_id=(
                relation.referenced_field_id.uuid
                if relation.referenced_field_id is not None
                else None
            ),
            referenced_field=(
                referenced_field.field_name.value
                if referenced_field is not None
                else None
            ),
            relation_table_name=relation.relation_table_name,
            source_join_column_name=relation.source_join_column_name,
            target_join_column_name=relation.target_join_column_name,
            on_delete=relation.on_delete,
            is_required=relation.is_required,
            is_unique=relation.is_unique,
            kind=relation.kind,
            settings=dict(relation.settings),
        )


__all__ = ["SchemaConfigRepository"]
