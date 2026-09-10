from __future__ import annotations

from src.modules.identity.application.ports import (
    TenantContextReaderPort,
    TenantRequestContext,
)
from src.modules.tenancy.application.tenant_domain.query import (
    ResolveTenantRequestContextByHostQuery,
)
from src.modules.tenancy.presentation.depends.application import (
    TenantRequestContextByHostUseCaseDep,
)


class TenancyTenantContextReaderAdapter(TenantContextReaderPort):
    """Адаптер identity-порта tenant context к tenancy use case."""

    def __init__(self, use_case: TenantRequestContextByHostUseCaseDep):
        """Инициализирует адаптер use case resolve tenant context по host."""
        self._use_case = use_case

    async def get_by_host(self, host: str) -> TenantRequestContext:
        """Возвращает identity TenantRequestContext, смэпленный из tenancy DTO."""
        result = await self._use_case.execute(
            ResolveTenantRequestContextByHostQuery(host=host)
        )
        return TenantRequestContext(
            tenant_id=result.tenant_id,
            tenant_domain_id=result.tenant_domain_id,
            host=result.host,
            tenant_status=result.tenant_status,
            domain_status=result.domain_status,
            api_host=result.api_host,
        )


__all__ = ["TenancyTenantContextReaderAdapter"]
