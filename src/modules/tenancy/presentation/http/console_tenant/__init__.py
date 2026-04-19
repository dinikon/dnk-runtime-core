from src.modules.tenancy.presentation.http.console_tenant.controller import (
    resolve_tenant_router,
)
from src.modules.tenancy.presentation.http.console_tenant.responses import (
    ResolveTenantResponseSchema,
)

__all__ = [
    "ResolveTenantResponseSchema",
    "resolve_tenant_router",
]
