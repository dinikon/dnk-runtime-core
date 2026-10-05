from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.tenancy.presentation.tenant_locale.http.controller.add_tenant_locale import (
    add_tenant_locale,
)
from src.modules.tenancy.presentation.tenant_locale.http.controller.list_system_locales import (
    list_system_locales,
)
from src.modules.tenancy.presentation.tenant_locale.http.controller.list_tenant_locales import (
    list_tenant_locales,
)
from src.modules.tenancy.presentation.tenant_locale.http.controller.remove_tenant_locale import (
    remove_tenant_locale,
)
from src.modules.tenancy.presentation.tenant_locale.http.response.system_locale import (
    SystemLocaleResponse,
)
from src.modules.tenancy.presentation.tenant_locale.http.response.tenant_locale import (
    TenantLocaleResponse,
)

router = APIRouter(prefix="/locales", tags=["tenant-locales"])
router.add_api_route(
    "/available",
    list_system_locales,
    methods=["GET"],
    response_model=list[SystemLocaleResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_tenant_locales,
    methods=["GET"],
    response_model=list[TenantLocaleResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    add_tenant_locale,
    methods=["POST"],
    status_code=201,
    response_model=TenantLocaleResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{code}",
    remove_tenant_locale,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
