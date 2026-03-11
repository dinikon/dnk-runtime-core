from __future__ import annotations

from uuid import UUID

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.use_case import (
    BootstrapTenantSystemSchemaUseCase,
)
from src.modules.tenancy.application.admin_onboarding.ports.runtime_schema import (
    TenantRuntimeSchemaBootstrapperProtocol,
)


class RuntimeSchemaBootstrapperAdapter(TenantRuntimeSchemaBootstrapperProtocol):
    def __init__(self, use_case: BootstrapTenantSystemSchemaUseCase):
        self._use_case = use_case

    async def bootstrap_tenant_system_schema(
        self,
        *,
        tenant_id: UUID,
        data_source_id: UUID,
        schema: str,
    ) -> None:
        await self._use_case.execute(
            BootstrapTenantSystemSchemaCommandDTO(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=schema,
            )
        )
