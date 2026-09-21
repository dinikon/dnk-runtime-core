from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.enabled_currency.command.disable_currency_command import (
    DisableCurrencyCommand,
)
from src.modules.currency.application.enabled_currency.command.enable_currency_command import (
    EnableCurrencyCommand,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.policy.error import (
    CurrencyConflict,
    CurrencyPolicyNotConfigured,
)
from src.modules.currency.presentation.depends.application import (
    EnableCurrencyUseCaseDep,
    DisableCurrencyUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.enabled_currency.requests.enabled_request import (
    EnabledRequest,
)
from src.modules.currency.presentation.http.settings.responses.settings_response import (
    ActionResponse,
)
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money_errors import InvalidCurrencyCodeError
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.put(
    "/enabled/{code}",
    dependencies=[Depends(require_csrf)],
    response_model=ActionResponse,
)
async def set_enabled_currency(
    context: AuthenticatedRequestContextDep,
    use_case: EnableCurrencyUseCaseDep,
    disable_use_case: DisableCurrencyUseCaseDep,
    code: str,
    payload: EnabledRequest,
):
    """HTTP entrypoint for set enabled currency."""
    if "currency.manage_enabled" not in permissions(context):
        raise HTTPException(
            403,
            {
                "code": "currency_forbidden",
                "message": "Currency permission is required.",
            },
        )
    tenant = EntityIdVO.from_value(context.principal.tenant_id)
    actor = EntityIdVO.from_value(context.principal.user_id)
    try:
        if payload.enabled:
            await use_case(EnableCurrencyCommand(tenant, actor, Code(code)))
        else:
            await disable_use_case(DisableCurrencyCommand(tenant, actor, Code(code)))
        return ActionResponse()
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyConflict as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyPolicyNotConfigured as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidCurrencyCodeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except OperationalError as exc:
        raise HTTPException(
            503,
            {
                "code": "currency_storage_unavailable",
                "message": "Currency storage is temporarily unavailable.",
            },
        ) from exc


__all__ = ["router"]
