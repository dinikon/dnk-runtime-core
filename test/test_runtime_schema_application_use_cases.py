from __future__ import annotations

import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.use_case import (
    BootstrapTenantSystemSchemaUseCase,
)
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
    DeleteFieldCommandDTO,
    UpdateFieldCommandDTO,
)
from src.modules.runtime_schema.application.field_definition.use_cases import (
    CreateFieldDefinitionUseCase,
    DeleteFieldDefinitionUseCase,
    UpdateFieldDefinitionUseCase,
)
from src.modules.runtime_schema.application.object_definition.dto import (
    CreateObjectCommandDTO,
    DeleteObjectCommandDTO,
    UpdateObjectCommandDTO,
)
from src.modules.runtime_schema.application.object_definition.use_cases import (
    CreateObjectDefinitionUseCase,
    DeleteObjectDefinitionUseCase,
    UpdateObjectDefinitionUseCase,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.use_case import (
    SyncTenantSystemSchemaUseCase,
)


class TestApplicationUseCases(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_and_sync_use_cases_delegate_to_orchestrator(self) -> None:
        orchestrator = AsyncMock()
        bootstrap_use_case = BootstrapTenantSystemSchemaUseCase(orchestrator=orchestrator)
        sync_use_case = SyncTenantSystemSchemaUseCase(orchestrator=orchestrator)

        bootstrap_dto = BootstrapTenantSystemSchemaCommandDTO(
            tenant_id=uuid4(),
            data_source_id=uuid4(),
            schema="tenant_schema",
        )
        sync_dto = SyncTenantSystemSchemaCommandDTO(
            tenant_id=uuid4(),
            data_source_id=uuid4(),
            schema="tenant_schema",
        )

        await bootstrap_use_case.execute(bootstrap_dto)
        await sync_use_case.execute(sync_dto)
        orchestrator.bootstrap_tenant_system_schema.assert_awaited_once()
        orchestrator.sync_tenant_system_schema.assert_awaited_once()

    async def test_object_use_cases_delegate(self) -> None:
        orchestrator = AsyncMock()
        create_use_case = CreateObjectDefinitionUseCase(orchestrator=orchestrator)
        update_use_case = UpdateObjectDefinitionUseCase(orchestrator=orchestrator)
        delete_use_case = DeleteObjectDefinitionUseCase(orchestrator=orchestrator)

        create_dto = CreateObjectCommandDTO(
            tenant_id=uuid4(),
            data_source_id=uuid4(),
            object_name_singular="lead",
        )
        update_dto = UpdateObjectCommandDTO(tenant_id=uuid4(), object_id=uuid4())
        delete_dto = DeleteObjectCommandDTO(tenant_id=uuid4(), object_id=uuid4())

        await create_use_case.execute(create_dto)
        await update_use_case.execute(update_dto)
        await delete_use_case.execute(delete_dto)

        orchestrator.create_object_definition.assert_awaited_once()
        orchestrator.update_object_definition.assert_awaited_once()
        orchestrator.delete_object_definition.assert_awaited_once()

    async def test_field_use_cases_delegate(self) -> None:
        orchestrator = AsyncMock()
        create_use_case = CreateFieldDefinitionUseCase(orchestrator=orchestrator)
        update_use_case = UpdateFieldDefinitionUseCase(orchestrator=orchestrator)
        delete_use_case = DeleteFieldDefinitionUseCase(orchestrator=orchestrator)

        create_dto = CreateFieldCommandDTO(
            tenant_id=uuid4(),
            object_id=uuid4(),
            field_type="string",
            field_name="title",
            label="Title",
        )
        update_dto = UpdateFieldCommandDTO(tenant_id=uuid4(), field_id=uuid4())
        delete_dto = DeleteFieldCommandDTO(tenant_id=uuid4(), field_id=uuid4())

        await create_use_case.execute(create_dto)
        await update_use_case.execute(update_dto)
        await delete_use_case.execute(delete_dto)

        orchestrator.create_field_definition.assert_awaited_once()
        orchestrator.update_field_definition.assert_awaited_once()
        orchestrator.delete_field_definition.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

