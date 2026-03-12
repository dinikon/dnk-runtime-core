from __future__ import annotations

from src.modules.runtime_schema.application.ports.orchestrator import (
    DdlOrchestratorServiceProtocol,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
    SyncTenantSystemSchemaResultDTO,
)


class SyncTenantSystemSchemaUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(
        self,
        dto: SyncTenantSystemSchemaCommandDTO,
    ) -> SyncTenantSystemSchemaResultDTO:
        return await self._orchestrator.sync_tenant_system_schema(dto=dto)

