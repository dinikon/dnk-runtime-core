from fastapi import HTTPException
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantUnavailableError,
)
from src.modules.identity.domain.access.error import IdentityAccessError


async def call(operation):
    try:
        return await operation
    except IdentityAccessError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    except IdentityTenantNotFoundError:
        raise HTTPException(404, "Workspace not found.") from None
    except IdentityTenantUnavailableError:
        raise HTTPException(403, "Workspace unavailable.") from None
