from fastapi import APIRouter, Depends, Request, Response
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.auth.providers import TenantContextReaderDep
from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.shared.presentation.tokens.depends import TokenManagerDep

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.get("/auth/csrf")
async def csrf(
    request: Request,
    response: Response,
    tokens: TokenManagerDep,
    host: RequestHostDep,
    tenant_reader: TenantContextReaderDep,
):
    await call(tenant_reader.get_by_host(host))
    return await issue_csrf(request, response, tokens)
