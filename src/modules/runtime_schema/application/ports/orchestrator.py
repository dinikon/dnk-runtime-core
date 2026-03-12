from __future__ import annotations

from typing import Protocol

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
    DeleteFieldCommandDTO,
    FieldDefinitionDTO,
    UpdateFieldCommandDTO,
)
from src.modules.runtime_schema.application.object_definition.dto import (
    CreateObjectCommandDTO,
    DeleteObjectCommandDTO,
    ObjectDefinitionDTO,
    UpdateObjectCommandDTO,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
    SyncTenantSystemSchemaResultDTO,
)


class DdlOrchestratorServiceProtocol(Protocol):
    async def bootstrap_tenant_system_schema(
        self,
        dto: BootstrapTenantSystemSchemaCommandDTO,
    ) -> SyncTenantSystemSchemaResultDTO: ...

    async def sync_tenant_system_schema(
        self,
        dto: SyncTenantSystemSchemaCommandDTO,
    ) -> SyncTenantSystemSchemaResultDTO: ...

    async def create_object_definition(
        self,
        dto: CreateObjectCommandDTO,
    ) -> ObjectDefinitionDTO: ...

    async def update_object_definition(
        self,
        dto: UpdateObjectCommandDTO,
    ) -> ObjectDefinitionDTO: ...

    async def delete_object_definition(self, dto: DeleteObjectCommandDTO) -> None: ...

    async def create_field_definition(
        self,
        dto: CreateFieldCommandDTO,
    ) -> FieldDefinitionDTO: ...

    async def update_field_definition(
        self,
        dto: UpdateFieldCommandDTO,
    ) -> FieldDefinitionDTO: ...

    async def delete_field_definition(self, dto: DeleteFieldCommandDTO) -> None: ...

