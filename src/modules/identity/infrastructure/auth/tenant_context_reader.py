from __future__ import annotations
from src.modules.tenancy.domain.tenant_domain.error import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
    IdentityTenantUnavailableError,
)

from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantRequestContext,
)
from src.modules.tenancy.application.tenant_domain.query.resolve_tenant_request_context_by_host_query import (
    ResolveTenantRequestContextByHostQuery,
)
from src.modules.tenancy.application.tenant_domain.use_case.resolve_tenant_request_context_by_host import (
    ResolveTenantRequestContextByHostUseCase,
)


class TenancyTenantContextReaderAdapter(TenantContextReaderPort):
    """Адаптер identity-порта tenant context к tenancy use case."""

    def __init__(self, use_case: ResolveTenantRequestContextByHostUseCase):
        """Инициализирует адаптер use case resolve tenant context по host."""
        self._use_case = use_case

    async def get_by_host(self, host: str) -> TenantRequestContext:
        """Возвращает identity TenantRequestContext, смэпленный из tenancy DTO."""
        try:
            result = await self._use_case.execute(
                ResolveTenantRequestContextByHostQuery(host=host)
            )
        except TenantHostNotFoundError as exc:
            raise IdentityTenantNotFoundError(str(exc)) from exc
        except TenantLoginUnavailableError as exc:
            raise IdentityTenantUnavailableError(str(exc)) from exc
        return TenantRequestContext(
            tenant_id=result.tenant_id,
            tenant_domain_id=result.tenant_domain_id,
            host=result.host,
            tenant_status=result.tenant_status,
            domain_status=result.domain_status,
            api_host=result.api_host,
        )


__all__ = ["TenancyTenantContextReaderAdapter"]
