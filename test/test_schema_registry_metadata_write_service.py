from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.application.metadata.schema_registry_metadata_write_service import (
    SchemaRegistryMetadataWriteService,
)
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.service import ObjectService
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
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedFieldSpec,
    ValidatedObjectSpec,
    ValidatedSchemaSpec,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.infrastructure.time import UtcClock


class SchemaRegistryMetadataWriteServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reconcile_preserves_matching_object_and_field_ids(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_crm"),
        )
        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Contacts.",
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="last_name",
            field_type=FieldTypeCatalog().from_seed_type("text"),
            label="Last Name",
            description="Last name.",
            is_nullable=False,
        )
        original_object_id = object_entity.id
        original_field_id = object_entity.fields[0].id

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return datasource

        class ObjectRepositoryStub:
            def __init__(self):
                self.objects = [object_entity]
                self.recorded_objects = []

            async def list_by_tenant_id(self, *, tenant_id):
                return self.objects

            async def reconcile_for_tenant(self, *, tenant_id, objects):
                self.recorded_objects = objects
                self.objects = objects

        object_repository = ObjectRepositoryStub()
        object_service = ObjectService(
            object_repository=object_repository,
            clock=UtcClock(),
            object_id_provider=lambda: RuntimeObjectIdVO.from_value(uuid4()),
            field_id_provider=lambda: RuntimeFieldIdVO.from_value(uuid4()),
            field_type_catalog=FieldTypeCatalog(),
        )

        class RelationServiceStub:
            async def clear_for_tenant(self, *, tenant_id):
                return None

            async def replace_all_for_tenant_from_spec(
                self, *, tenant_id, data_source_id, schema_spec, objects
            ):
                return []

        service = SchemaRegistryMetadataWriteService(
            data_source_service=DataSourceServiceStub(),
            object_service=object_service,
            relation_service=RelationServiceStub(),
        )
        schema_spec = ValidatedSchemaSpec(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ValidatedObjectSpec(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    kind=ObjectKind.CUSTOM,
                    fields=(
                        ValidatedFieldSpec(
                            name="last_name",
                            type="text",
                            kind=FieldKind.SYSTEM,
                            field_type=FieldTypeCatalog().from_seed_type("text"),
                            label="Last Name",
                            description="Last name.",
                            is_nullable=False,
                            default=None,
                            options={},
                            settings={},
                        ),
                    ),
                ),
            ),
        )

        await service.reconcile_from_spec(
            tenant_id=tenant_id,
            schema_spec=schema_spec,
        )

        reconciled_object = object_repository.recorded_objects[0]
        self.assertEqual(reconciled_object.id, original_object_id)
        self.assertEqual(reconciled_object.fields[0].id, original_field_id)
        self.assertEqual(reconciled_object.kind, ObjectKind.CUSTOM)
        self.assertEqual(reconciled_object.fields[0].kind, FieldKind.SYSTEM)

    async def test_reconcile_preserves_custom_objects_outside_seed(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_crm"),
        )
        standard_object = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Contacts.",
            kind=ObjectKind.STANDARD,
        )
        custom_object = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            now=now,
            object_name=ObjectNameVO(singular="c_deal", plural="c_deals"),
            object_label=ObjectLabelVO(singular="Deal", plural="Deals"),
            description="Deals.",
            kind=ObjectKind.CUSTOM,
        )
        original_custom_id = custom_object.id

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return datasource

        class ObjectRepositoryStub:
            def __init__(self):
                self.objects = [standard_object, custom_object]
                self.recorded_objects = []

            async def list_by_tenant_id(self, *, tenant_id):
                return self.objects

            async def reconcile_for_tenant(self, *, tenant_id, objects):
                self.recorded_objects = objects
                self.objects = objects

        object_repository = ObjectRepositoryStub()
        object_service = ObjectService(
            object_repository=object_repository,
            clock=UtcClock(),
            object_id_provider=lambda: RuntimeObjectIdVO.from_value(uuid4()),
            field_id_provider=lambda: RuntimeFieldIdVO.from_value(uuid4()),
            field_type_catalog=FieldTypeCatalog(),
        )

        class RelationServiceStub:
            async def clear_for_tenant(self, *, tenant_id):
                return None

            async def replace_all_for_tenant_from_spec(
                self, *, tenant_id, data_source_id, schema_spec, objects
            ):
                return []

        service = SchemaRegistryMetadataWriteService(
            data_source_service=DataSourceServiceStub(),
            object_service=object_service,
            relation_service=RelationServiceStub(),
        )
        schema_spec = ValidatedSchemaSpec(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ValidatedObjectSpec(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    kind=ObjectKind.STANDARD,
                    fields=(),
                ),
            ),
        )

        await service.reconcile_from_spec(
            tenant_id=tenant_id,
            schema_spec=schema_spec,
        )

        self.assertEqual(
            [item.object_name.plural for item in object_repository.recorded_objects],
            ["contacts", "c_deals"],
        )
        self.assertEqual(object_repository.recorded_objects[1].id, original_custom_id)
        self.assertIs(object_repository.recorded_objects[1], custom_object)

    async def test_reconcile_prunes_relations_before_removing_objects(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_crm"),
        )
        retired_object = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Contacts.",
            kind=ObjectKind.STANDARD,
        )
        retained_object = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource.id,
            now=now,
            object_name=ObjectNameVO(singular="c_deal", plural="c_deals"),
            object_label=ObjectLabelVO(singular="Deal", plural="Deals"),
            description="Deals.",
            kind=ObjectKind.CUSTOM,
        )
        calls: list[str] = []

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return datasource

        class ObjectServiceStub:
            async def list_by_tenant_id(self, *, tenant_id):
                calls.append("list-objects")
                return [retired_object, retained_object]

            async def reconcile_for_tenant_from_spec(
                self, *, tenant_id, data_source_id, schema_spec
            ):
                calls.append("reconcile-objects")
                return [retained_object]

        class RelationServiceStub:
            async def prune_for_retained_members(
                self, *, tenant_id, retained_object_ids, retained_field_ids
            ):
                calls.append("prune-relations")
                self.retained_object_ids = retained_object_ids
                return []

            async def reconcile_for_tenant_from_spec(
                self, *, tenant_id, data_source_id, schema_spec, objects
            ):
                calls.append("reconcile-relations")
                return []

        relation_service = RelationServiceStub()
        service = SchemaRegistryMetadataWriteService(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),  # type: ignore[arg-type]
            relation_service=relation_service,  # type: ignore[arg-type]
        )

        await service.reconcile_from_spec(
            tenant_id=tenant_id,
            schema_spec=ValidatedSchemaSpec(
                version=None,
                code="crm",
                label="CRM",
                objects=(),
            ),
        )

        self.assertEqual(
            calls,
            [
                "list-objects",
                "prune-relations",
                "reconcile-objects",
                "reconcile-relations",
            ],
        )
        self.assertEqual(relation_service.retained_object_ids, {retained_object.id})
