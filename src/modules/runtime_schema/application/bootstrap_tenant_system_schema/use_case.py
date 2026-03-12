from __future__ import annotations

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.ports.orchestrator import (
    DdlOrchestratorServiceProtocol,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaResultDTO,
)


class BootstrapTenantSystemSchemaUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(
        self,
        dto: BootstrapTenantSystemSchemaCommandDTO,
    ) -> SyncTenantSystemSchemaResultDTO:
        return await self._orchestrator.bootstrap_tenant_system_schema(dto=dto)

