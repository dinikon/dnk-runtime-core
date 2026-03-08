import unittest
from uuid import UUID, uuid4

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.use_case import (
    BootstrapTenantSystemSchemaUseCase,
)
from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
    SystemFieldDefinition,
    SystemObjectDefinition,
)
from src.modules.runtime_schema.domain.errors import SystemRelationDefinitionError
from src.modules.runtime_schema.domain.value_objects import (
    RuntimeSchemaFieldType,
    RuntimeSchemaRelationKind,
)
from src.modules.runtime_schema.infrastructure.system_definitions import (
    StaticSystemObjectDefinitionsProvider,
)


class RuntimeSchemaBootstrapTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_creates_system_metadata_and_is_idempotent(self) -> None:
        objects_repository = InMemoryObjectMetadataRepository()
        fields_repository = InMemoryFieldMetadataRepository()
        relations_repository = InMemoryRelationMetadataRepository()
        schema_manager = InMemoryTenantSchemaManager()
        use_case = BootstrapTenantSystemSchemaUseCase(
            object_metadata_repository=objects_repository,
            field_metadata_repository=fields_repository,
            relation_metadata_repository=relations_repository,
            system_object_definitions_provider=StaticSystemObjectDefinitionsProvider(),
            tenant_schema_manager=schema_manager,
        )
        dto = BootstrapTenantSystemSchemaCommandDTO(
            tenant_id=uuid4(),
            data_source_id=uuid4(),
            schema="dnk_schema_test",
        )

        first_result = await use_case.execute(dto)
        second_result = await use_case.execute(dto)

        self.assertEqual(first_result.objects_created, 4)
        self.assertEqual(first_result.fields_created, 33)
        self.assertEqual(second_result.objects_created, 0)
        self.assertEqual(second_result.fields_created, 0)
        self.assertEqual(len(objects_repository.items), 4)
        self.assertEqual(len(fields_repository.items), 33)
        self.assertEqual(len(relations_repository.items), 2)
        self.assertEqual(len(schema_manager.ensured_system_objects), 8)
        self.assertEqual(len(schema_manager.ensured_relations), 4)
        for object_metadata in objects_repository.items.values():
            self.assertIsNotNone(object_metadata.label_identifier_field_metadata_id)

    async def test_bootstrap_rejects_invalid_system_relation_definition(self) -> None:
        objects_repository = InMemoryObjectMetadataRepository()
        fields_repository = InMemoryFieldMetadataRepository()
        relations_repository = InMemoryRelationMetadataRepository()
        schema_manager = InMemoryTenantSchemaManager()
        use_case = BootstrapTenantSystemSchemaUseCase(
            object_metadata_repository=objects_repository,
            field_metadata_repository=fields_repository,
            relation_metadata_repository=relations_repository,
            system_object_definitions_provider=InvalidSystemDefinitionsProvider(),
            tenant_schema_manager=schema_manager,
        )

        with self.assertRaises(SystemRelationDefinitionError):
            await use_case.execute(
                BootstrapTenantSystemSchemaCommandDTO(
                    tenant_id=uuid4(),
                    data_source_id=uuid4(),
                    schema="dnk_schema_test",
                )
            )


class InMemoryObjectMetadataRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ObjectMetadata] = {}

    async def add(self, object_metadata: ObjectMetadata) -> None:
        self.items[object_metadata.id] = object_metadata

    async def save(self, object_metadata: ObjectMetadata) -> None:
        self.items[object_metadata.id] = object_metadata

    async def get_by_id(self, object_metadata_id: UUID) -> ObjectMetadata | None:
        return self.items.get(object_metadata_id)

    async def get_by_tenant_and_name_singular(
        self,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None:
        for item in self.items.values():
            if item.tenant_id == tenant_id and item.name_singular == name_singular:
                return item
        return None


class InMemoryFieldMetadataRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, FieldMetadata] = {}

    async def add(self, field_metadata: FieldMetadata) -> None:
        self.items[field_metadata.id] = field_metadata

    async def save(self, field_metadata: FieldMetadata) -> None:
        self.items[field_metadata.id] = field_metadata

    async def get_by_id(self, field_metadata_id: UUID) -> FieldMetadata | None:
        return self.items.get(field_metadata_id)

    async def get_by_object_and_name_field(
        self,
        object_metadata_id: UUID,
        name_field: str,
    ) -> FieldMetadata | None:
        for item in self.items.values():
            if (
                item.object_metadata_id == object_metadata_id
                and item.name_field == name_field
            ):
                return item
        return None


class InMemoryRelationMetadataRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, RelationMetadata] = {}

    async def add(self, relation_metadata: RelationMetadata) -> None:
        self.items[relation_metadata.id] = relation_metadata

    async def save(self, relation_metadata: RelationMetadata) -> None:
        self.items[relation_metadata.id] = relation_metadata

    async def get_by_id(self, relation_id: UUID) -> RelationMetadata | None:
        return self.items.get(relation_id)

    async def get_by_source_field_id(
        self,
        source_field_metadata_id: UUID,
    ) -> RelationMetadata | None:
        for item in self.items.values():
            if (
                item.source_field_metadata_id == source_field_metadata_id
                and item.is_active
            ):
                return item
        return None

    async def exists_by_junction_table_name(
        self,
        junction_table_name: str,
    ) -> bool:
        return any(
            item.junction_table_name == junction_table_name and item.is_active
            for item in self.items.values()
        )


class InMemoryTenantSchemaManager:
    def __init__(self) -> None:
        self.ensured_system_objects: list[str] = []
        self.ensured_relations: list[UUID] = []

    async def ensure_system_object(self, *, schema: str, object_definition) -> None:
        self.ensured_system_objects.append(f"{schema}:{object_definition.table_name}")

    async def ensure_relation(self, *, schema: str, relation, **kwargs) -> None:
        self.ensured_relations.append(relation.id)

    async def drop_relation(self, **kwargs) -> None:
        raise AssertionError("drop_relation should not be called during bootstrap")


class InvalidSystemDefinitionsProvider:
    def get_system_objects(self) -> tuple[SystemObjectDefinition, ...]:
        return (
            SystemObjectDefinition(
                name_singular="lead",
                name_plural="leads",
                label_singular="Lead",
                label_plural="Leads",
                table_name="crm_leads",
                label_identifier_field_name="title",
                fields=(
                    SystemFieldDefinition(
                        name_field="id",
                        column_name="id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="ID",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    SystemFieldDefinition(
                        name_field="title",
                        column_name="title",
                        field_type=RuntimeSchemaFieldType.STRING,
                        label="Title",
                        is_nullable=False,
                    ),
                    SystemFieldDefinition(
                        name_field="missing_company_id",
                        column_name="missing_company_id",
                        field_type=RuntimeSchemaFieldType.UUID,
                        label="Company",
                        is_nullable=True,
                        relation_kind=RuntimeSchemaRelationKind.MANY_TO_ONE,
                        relation_target_object_name_singular="company",
                        relation_target_field_name="id",
                    ),
                ),
            ),
        )
