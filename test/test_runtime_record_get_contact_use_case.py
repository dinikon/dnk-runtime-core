from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from sqlalchemy import select, text

from src.modules.crm.application.use_case.contact.get_contact_use_case import (
    GetContactQueryDTO,
    GetContactUseCase,
)
from src.modules.crm.domain.error import ContactNotFoundError
from src.modules.runtime_record.infrastructure.factory import (
    build_runtime_record_reader,
)
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.runtime_schema.infrastructure.persistence.models import (
    ObjectMetadataModel,
)
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from test.runtime_schema_test_utils import sqlite_session


class TestGetContactUseCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tenant_id = uuid4()
        self.data_source_id = uuid4()
        self.schema = "tenant_test"

    async def test_get_contact_returns_system_and_custom_fields(self) -> None:
        async with sqlite_session() as session:
            session.add(
                TenantDataSourceModel(
                    id=self.data_source_id,
                    tenant_id=self.tenant_id,
                    type="sqlite",
                    is_remote=False,
                    dsn=None,
                    schema=self.schema,
                )
            )
            await session.flush()

            orchestrator = build_ddl_orchestrator(session=session)
            await orchestrator.sync_tenant_system_schema(
                SyncTenantSystemSchemaCommandDTO(
                    tenant_id=self.tenant_id,
                    data_source_id=self.data_source_id,
                    schema=self.schema,
                )
            )

            contact_object_id = await session.scalar(
                select(ObjectMetadataModel.id)
                .where(ObjectMetadataModel.tenant_id == str(self.tenant_id))
                .where(ObjectMetadataModel.data_source_id == str(self.data_source_id))
                .where(ObjectMetadataModel.name_singular == "contact")
                .limit(1)
            )
            assert contact_object_id is not None
            if isinstance(contact_object_id, UUID):
                parsed_contact_object_id = contact_object_id
            else:
                parsed_contact_object_id = UUID(str(contact_object_id))

            await orchestrator.create_field_definition(
                CreateFieldCommandDTO(
                    tenant_id=self.tenant_id,
                    object_id=parsed_contact_object_id,
                    schema=self.schema,
                    field_type="string",
                    field_name="nickname",
                    label="Nickname",
                    is_system=False,
                    is_custom=True,
                    is_nullable=True,
                )
            )

            contact_id = uuid4()
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__contacts" '
                    '("id", "name_first_name", "name_last_name", "name_middle_name", "nickname") '
                    "VALUES (:id, :first_name, :last_name, :middle_name, :nickname)"
                ),
                {
                    "id": str(contact_id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "middle_name": "Michael",
                    "nickname": "JD",
                },
            )
            await session.flush()

            runtime_record_reader = build_runtime_record_reader(session=session)
            use_case = GetContactUseCase(runtime_record_reader=runtime_record_reader)

            result = await use_case.execute(
                GetContactQueryDTO(
                    tenant_id=self.tenant_id,
                    contact_id=contact_id,
                )
            )

            self.assertEqual(result.contact.id.value, contact_id)
            self.assertEqual(result.contact.first_name, "John")
            self.assertEqual(result.contact.last_name, "Doe")
            self.assertEqual(result.contact.middle_name, "Michael")
            self.assertEqual(result.custom_fields.get("nickname"), "JD")

    async def test_get_contact_raises_when_not_found(self) -> None:
        async with sqlite_session() as session:
            session.add(
                TenantDataSourceModel(
                    id=self.data_source_id,
                    tenant_id=self.tenant_id,
                    type="sqlite",
                    is_remote=False,
                    dsn=None,
                    schema=self.schema,
                )
            )
            await session.flush()

            orchestrator = build_ddl_orchestrator(session=session)
            await orchestrator.sync_tenant_system_schema(
                SyncTenantSystemSchemaCommandDTO(
                    tenant_id=self.tenant_id,
                    data_source_id=self.data_source_id,
                    schema=self.schema,
                )
            )

            runtime_record_reader = build_runtime_record_reader(session=session)
            use_case = GetContactUseCase(runtime_record_reader=runtime_record_reader)

            with self.assertRaises(ContactNotFoundError):
                await use_case.execute(
                    GetContactQueryDTO(
                        tenant_id=self.tenant_id,
                        contact_id=uuid4(),
                    )
                )


if __name__ == "__main__":
    unittest.main()
