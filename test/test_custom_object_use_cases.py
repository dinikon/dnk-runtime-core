from __future__ import annotations

import unittest
from uuid import uuid4

from sqlalchemy import text

from src.modules.custom_object.application.commands import (
    CreateCustomObjectCommandDTO,
    CreateCustomObjectFieldCommandDTO,
)
from src.modules.custom_object.application.queries import GetCustomObjectRecordQueryDTO
from src.modules.custom_object.application.use_case import (
    CreateCustomObjectFieldUseCase,
    CreateCustomObjectUseCase,
    GetCustomObjectRecordUseCase,
)
from src.modules.custom_object.application.services import CustomObjectRuntimeRecordMapper
from src.modules.custom_object.domain import CustomObjectNotFoundError
from src.modules.custom_object.infrastructure.repositories import (
    RuntimeRecordCustomObjectRepository,
    RuntimeSchemaCustomObjectRepository,
)
from src.modules.runtime_record.infrastructure.factory import build_runtime_record_reader
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from test.runtime_schema_test_utils import sqlite_session


class TestCustomObjectUseCases(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tenant_id = uuid4()
        self.data_source_id = uuid4()
        self.schema = "tenant_test"

    async def test_create_custom_object_add_field_and_get_record(self) -> None:
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

            schema_repository = RuntimeSchemaCustomObjectRepository(
                session=session,
                orchestrator=orchestrator,
            )
            create_object_use_case = CreateCustomObjectUseCase(
                repository=schema_repository
            )
            create_field_use_case = CreateCustomObjectFieldUseCase(
                repository=schema_repository
            )

            created_object = await create_object_use_case.execute(
                CreateCustomObjectCommandDTO(
                    tenant_id=self.tenant_id,
                    object_name_singular="request",
                    object_name_plural="requests",
                    object_label_singular="Request",
                    object_label_plural="Requests",
                )
            )
            self.assertEqual(created_object.object_name_singular, "request")

            created_title_field = await create_field_use_case.execute(
                CreateCustomObjectFieldCommandDTO(
                    tenant_id=self.tenant_id,
                    object_name_singular="request",
                    field_type="string",
                    field_name="title",
                    label="Title",
                    is_nullable=False,
                )
            )
            self.assertEqual(created_title_field.field_name, "title")

            created_contact_relation = await create_field_use_case.execute(
                CreateCustomObjectFieldCommandDTO(
                    tenant_id=self.tenant_id,
                    object_name_singular="request",
                    field_type="relation",
                    field_name="contact_id",
                    label="Contact",
                    relation_target_object_name="contact",
                    settings={"on_delete": "cascade"},
                )
            )
            self.assertEqual(created_contact_relation.field_name, "contact_id")

            contact_id = uuid4()
            request_id = uuid4()
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__contacts" '
                    '("id", "name_first_name", "name_last_name", "name_middle_name") '
                    "VALUES (:id, :first_name, :last_name, :middle_name)"
                ),
                {
                    "id": str(contact_id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "middle_name": "Michael",
                },
            )
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__requests" '
                    '("id", "title", "contact_id") '
                    "VALUES (:id, :title, :contact_id)"
                ),
                {
                    "id": str(request_id),
                    "title": "Need approval",
                    "contact_id": str(contact_id),
                },
            )
            await session.flush()

            runtime_record_reader = build_runtime_record_reader(session=session)
            record_repository = RuntimeRecordCustomObjectRepository(
                session=session,
                runtime_record_reader=runtime_record_reader,
                mapper=CustomObjectRuntimeRecordMapper(),
            )
            get_record_use_case = GetCustomObjectRecordUseCase(
                repository=record_repository
            )

            result = await get_record_use_case.execute(
                GetCustomObjectRecordQueryDTO(
                    tenant_id=self.tenant_id,
                    object_name_singular="request",
                    record_id=request_id,
                )
            )
            self.assertEqual(result.object_name_singular, "request")
            self.assertEqual(result.record_id, request_id)
            self.assertEqual(result.values.get("title"), "Need approval")
            self.assertEqual(str(result.values.get("contact_id")), str(contact_id))

    async def test_system_object_is_not_available_in_custom_object_use_case(self) -> None:
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

            contact_id = uuid4()
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__contacts" '
                    '("id", "name_first_name", "name_last_name", "name_middle_name") '
                    "VALUES (:id, :first_name, :last_name, :middle_name)"
                ),
                {
                    "id": str(contact_id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "middle_name": "Michael",
                },
            )
            await session.flush()

            runtime_record_reader = build_runtime_record_reader(session=session)
            record_repository = RuntimeRecordCustomObjectRepository(
                session=session,
                runtime_record_reader=runtime_record_reader,
                mapper=CustomObjectRuntimeRecordMapper(),
            )
            get_record_use_case = GetCustomObjectRecordUseCase(
                repository=record_repository
            )

            with self.assertRaises(CustomObjectNotFoundError):
                await get_record_use_case.execute(
                    GetCustomObjectRecordQueryDTO(
                        tenant_id=self.tenant_id,
                        object_name_singular="contact",
                        record_id=contact_id,
                    )
                )


if __name__ == "__main__":
    unittest.main()
