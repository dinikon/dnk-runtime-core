from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.application.metadata.schema_registry_metadata_read_service import (
    SchemaRegistryMetadataReadService,
)
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.error import (
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.infrastructure.time import UtcClock


class SchemaRegistryMetadataReadServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_consistent_metadata_snapshot(self) -> None:
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

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return datasource

        class ObjectServiceStub:
            async def list_by_tenant_id(self, *, tenant_id):
                return [object_entity]

        service = SchemaRegistryMetadataReadService(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        snapshot = await service.get_required_by_tenant(tenant_id=tenant_id)

        self.assertEqual(snapshot.datasource.id, datasource.id)
        self.assertEqual(len(snapshot.objects), 1)

    async def test_rejects_inconsistent_object_data_source(self) -> None:
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
            data_source_id=DataSourceIdVO.from_value(uuid4()),
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Contacts.",
        )

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                return datasource

        class ObjectServiceStub:
            async def list_by_tenant_id(self, *, tenant_id):
                return [object_entity]

        service = SchemaRegistryMetadataReadService(
            data_source_service=DataSourceServiceStub(),
            object_service=ObjectServiceStub(),
        )

        with self.assertRaises(SchemaRegistryMetadataInconsistentError):
            await service.get_required_by_tenant(tenant_id=tenant_id)
