from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.entity import ObjectEntity
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
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.runtime import SchemaRegistryRuntimeObjectResolver
from src.modules.shared import EntityIdVO
from src.modules.shared.infrastructure.time import UtcClock


class SchemaRegistryRuntimeObjectResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_returns_descriptor_from_metadata(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        data_source = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )

        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contacts.",
            kind=ObjectKind.CUSTOM,
        )
        field_types = FieldTypeCatalog()
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="id",
            field_type=field_types.from_seed_type("uuid"),
            label="ID",
            description="Contact identifier.",
            is_nullable=False,
            default_value="gen_random_uuid()",
            kind=FieldKind.SYSTEM,
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="last_name",
            field_type=field_types.from_seed_type("text"),
            label="Last Name",
            description="Contact last name.",
            is_nullable=False,
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="tags",
            field_type=field_types.from_seed_type("multiselect"),
            label="Tags",
            description="Contact tags.",
            is_nullable=True,
            options={"vip": "VIP"},
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="payload",
            field_type=field_types.from_seed_type("json"),
            label="Payload",
            description="Internal payload.",
            is_nullable=True,
            settings={"is_filterable": "true", "is_sortable": "false"},
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_tenant_and_singular_name(
                self, *, tenant_id, singular_name
            ):
                if singular_name == "contact":
                    return object_entity
                return None

        resolver = SchemaRegistryRuntimeObjectResolver(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        descriptor = await resolver.resolve(
            tenant_id=tenant_id,
            object_name="contact",
        )

        self.assertEqual(descriptor.schema_name, "dnk_test")
        self.assertEqual(descriptor.object_name, "contact")
        self.assertEqual(descriptor.table_name, "contacts")
        self.assertEqual(descriptor.kind, "custom")
        self.assertEqual(descriptor.pk, "id")
        self.assertEqual(descriptor.title_field, "id")
        self.assertEqual(
            [field.name for field in descriptor.fields],
            ["id", "last_name", "tags", "payload"],
        )
        self.assertEqual(
            [field.kind for field in descriptor.fields],
            ["system", "standard", "standard", "standard"],
        )
        fields_by_name = descriptor.fields_by_name
        self.assertTrue(fields_by_name["id"].is_filterable)
        self.assertTrue(fields_by_name["id"].is_sortable)
        self.assertTrue(fields_by_name["last_name"].is_filterable)
        self.assertTrue(fields_by_name["last_name"].is_sortable)
        self.assertTrue(fields_by_name["tags"].is_filterable)
        self.assertFalse(fields_by_name["tags"].is_sortable)
        self.assertTrue(fields_by_name["payload"].is_filterable)
        self.assertFalse(fields_by_name["payload"].is_sortable)

    async def test_resolve_includes_relation_descriptors_from_metadata(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        data_source = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )
        field_types = FieldTypeCatalog()
        company = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            now=now,
            object_name=ObjectNameVO(singular="company", plural="companies"),
            object_label=ObjectLabelVO(singular="Company", plural="Companies"),
            description="Companies.",
        )
        company.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="id",
            field_type=field_types.from_seed_type("uuid"),
            label="ID",
            description="Company identifier.",
            is_nullable=False,
            default_value="gen_random_uuid()",
            kind=FieldKind.SYSTEM,
        )
        contact = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Contacts.",
        )
        contact.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="id",
            field_type=field_types.from_seed_type("uuid"),
            label="ID",
            description="Contact identifier.",
            is_nullable=False,
            default_value="gen_random_uuid()",
            kind=FieldKind.SYSTEM,
        )
        contact.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="company_id",
            field_type=field_types.from_seed_type("reference"),
            label="Company ID",
            description="Company reference.",
            is_nullable=True,
        )
        relation = RelationEntity.create(
            id_=RuntimeRelationIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name="contacts_company",
            relation_type=RelationTypeEnum.MANY_TO_ONE,
            source_object_id=contact.id,
            target_object_id=company.id,
            owning_object_id=contact.id,
            fk_field_id=contact.fields[1].id,
            referenced_object_id=company.id,
            referenced_field_id=company.fields[0].id,
            source_relation_name="company",
            target_relation_name="contacts",
            relation_table_name=None,
            source_join_column_name=None,
            target_join_column_name=None,
            on_delete="set_null",
            is_required=False,
            is_unique=False,
            kind="standard",
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_tenant_and_singular_name(
                self, *, tenant_id, singular_name
            ):
                if singular_name == "contact":
                    return contact
                return None

            async def list_by_tenant_id(self, *, tenant_id):
                return [company, contact]

        class RelationServiceStub:
            async def list_by_tenant_id(self, *, tenant_id):
                return [relation]

        resolver = SchemaRegistryRuntimeObjectResolver(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
            relation_service=RelationServiceStub(),
        )

        descriptor = await resolver.resolve(
            tenant_id=tenant_id,
            object_name="contact",
        )

        self.assertEqual(len(descriptor.relations), 1)
        relation_descriptor = descriptor.relations[0]
        self.assertEqual(relation_descriptor.name, "contacts_company")
        self.assertEqual(relation_descriptor.relation_type, "many_to_one")
        self.assertEqual(relation_descriptor.source_object, "contacts")
        self.assertEqual(relation_descriptor.target_object, "companies")
        self.assertEqual(relation_descriptor.fk_field, "company_id")
        self.assertFalse(relation_descriptor.is_collection)
        self.assertFalse(relation_descriptor.is_virtual)

    async def test_resolve_by_id_returns_descriptor_from_metadata(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        data_source = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )
        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            now=now,
            object_name=ObjectNameVO(singular="deal", plural="deals"),
            object_label=ObjectLabelVO(singular="Deal", plural="Deals"),
            description="Tenant deals.",
            kind=ObjectKind.CUSTOM,
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="id",
            field_type=FieldTypeCatalog().from_seed_type("uuid"),
            label="ID",
            description="Deal identifier.",
            is_nullable=False,
            default_value="gen_random_uuid()",
            kind=FieldKind.SYSTEM,
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_id(self, *, object_id):
                if object_id == object_entity.id:
                    return object_entity
                return None

        resolver = SchemaRegistryRuntimeObjectResolver(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        descriptor = await resolver.resolve_by_id(
            tenant_id=tenant_id,
            object_id=object_entity.id,
        )

        self.assertEqual(descriptor.object_name, "deal")
        self.assertEqual(descriptor.table_name, "deals")

    async def test_resolve_raises_not_found(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        data_source = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_tenant_and_singular_name(
                self, *, tenant_id, singular_name
            ):
                return None

        resolver = SchemaRegistryRuntimeObjectResolver(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        with self.assertRaises(RuntimeObjectNotFoundError):
            await resolver.resolve(
                tenant_id=tenant_id,
                object_name="contact",
            )

    async def test_resolve_rejects_missing_id_field(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        data_source = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )

        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contacts.",
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="last_name",
            field_type=FieldTypeCatalog().from_seed_type("text"),
            label="Last Name",
            description="Contact last name.",
            is_nullable=False,
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_tenant_and_singular_name(
                self, *, tenant_id, singular_name
            ):
                return object_entity

        resolver = SchemaRegistryRuntimeObjectResolver(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        with self.assertRaises(RuntimeObjectDescriptorError):
            await resolver.resolve(tenant_id=tenant_id, object_name="contact")

    async def test_resolve_rejects_metadata_mismatch(self) -> None:
        now = UtcClock().now()
        tenant_id = EntityIdVO.from_value(uuid4())
        data_source = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )

        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=DataSourceIdVO.from_value(uuid4()),
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contacts.",
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="id",
            field_type=FieldTypeCatalog().from_seed_type("uuid"),
            label="ID",
            description="Contact identifier.",
            is_nullable=False,
            default_value="gen_random_uuid()",
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_tenant_and_singular_name(
                self, *, tenant_id, singular_name
            ):
                return object_entity

        resolver = SchemaRegistryRuntimeObjectResolver(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        with self.assertRaises(SchemaRegistryMetadataInconsistentError):
            await resolver.resolve(tenant_id=tenant_id, object_name="contact")
