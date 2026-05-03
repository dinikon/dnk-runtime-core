from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.application.use_case.describe_runtime_object_use_case import (
    DescribeRuntimeObjectUseCase,
)
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.error import (
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
from src.modules.shared import EntityIdVO
from src.modules.shared.infrastructure.time import UtcClock


class DescribeRuntimeObjectUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_object_and_field_descriptions(self) -> None:
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
            description="Tenant contact registry.",
            kind=ObjectKind.STANDARD,
        )
        field_types = FieldTypeCatalog()
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="status",
            field_type=field_types.from_seed_type("select"),
            label="Status",
            description="Contact status.",
            is_nullable=False,
            default_value="'lead'",
            options={
                "lead": "Lead",
                "customer": "Customer",
            },
            kind=FieldKind.SYSTEM,
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="tags",
            field_type=field_types.from_seed_type("multiselect"),
            label="Tags",
            description="Contact tags.",
            is_nullable=True,
            options={
                "vip": "VIP",
            },
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

        use_case = DescribeRuntimeObjectUseCase(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        description = await use_case(tenant_id=tenant_id, object_name="contact")

        self.assertEqual(description.id, object_entity.id.uuid)
        self.assertEqual(description.singular_label, "Contact")
        self.assertEqual(description.plural_label, "Contacts")
        self.assertEqual(description.description, "Tenant contact registry.")
        self.assertEqual(description.kind, "standard")
        self.assertEqual(
            [field.field_name for field in description.fields],
            ["status", "tags"],
        )
        self.assertEqual(description.fields[0].type, "select")
        self.assertEqual(description.fields[0].kind, "system")
        self.assertEqual(description.fields[1].kind, "standard")
        self.assertEqual(description.fields[0].default_value, "'lead'")
        self.assertEqual(
            description.fields[0].options,
            {
                "lead": "Lead",
                "customer": "Customer",
            },
        )

    async def test_raises_not_found_when_object_is_absent(self) -> None:
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

        use_case = DescribeRuntimeObjectUseCase(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        with self.assertRaises(RuntimeObjectNotFoundError):
            await use_case(tenant_id=tenant_id, object_name="contact")

    async def test_raises_when_metadata_is_inconsistent(self) -> None:
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
            tenant_id=EntityIdVO.from_value(uuid4()),
            data_source_id=DataSourceIdVO.from_value(uuid4()),
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contact registry.",
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return data_source

        class ObjectServiceStub:
            async def get_by_tenant_and_singular_name(
                self, *, tenant_id, singular_name
            ):
                return object_entity

        use_case = DescribeRuntimeObjectUseCase(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        with self.assertRaises(SchemaRegistryMetadataInconsistentError):
            await use_case(tenant_id=tenant_id, object_name="contact")
