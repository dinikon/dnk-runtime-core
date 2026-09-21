from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.exc import OperationalError
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.money_errors import InvalidCurrencyCodeError
from src.modules.identity.domain.user.value_object import UserIdVO
from src.modules.identity.domain.auth import InvalidSessionError
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.identity.presentation.depends.display_currency import (
    SetDisplayCurrencyUseCaseDep,
)
from src.modules.identity.application.user.command.set_display_currency_command import (
    SetDisplayCurrencyCommand,
)
from src.modules.identity.presentation.http.console_auth.requests.display_currency_request import (
    DisplayCurrencyRequest,
)
from src.modules.identity.presentation.http.console_auth.responses.display_currency_response import (
    DisplayCurrencyResponse,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured

router = APIRouter()


@router.put(
    "/me/display-currency",
    response_model=DisplayCurrencyResponse,
    dependencies=[Depends(require_csrf)],
)
async def set_display_currency(
    payload: DisplayCurrencyRequest,
    context: AuthenticatedRequestContextDep,
    use_case: SetDisplayCurrencyUseCaseDep,
) -> DisplayCurrencyResponse:
    """Change only the authenticated user's preference."""
    if not {"member", "admin"}.intersection(context.principal.roles):
        raise HTTPException(
            403, {"code": "currency_forbidden", "message": "Membership is required."}
        )
    try:
        result = await use_case(
            SetDisplayCurrencyCommand(
                EntityIdVO.from_value(context.principal.tenant_id),
                UserIdVO.from_value(context.principal.user_id),
                (
                    CurrencyCodeVO(payload.display_currency)
                    if payload.display_currency
                    else None
                ),
            )
        )
    except InvalidSessionError as exc:
        raise HTTPException(401, "Unauthorized.") from exc
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except (
        CurrencyDisabled,
        CurrencyPolicyNotConfigured,
        InvalidCurrencyCodeError,
    ) as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except OperationalError as exc:
        raise HTTPException(
            503,
            {
                "code": "currency_storage_unavailable",
                "message": "Currency storage is temporarily unavailable.",
            },
        ) from exc
    return DisplayCurrencyResponse(
        display_currency=(
            str(result.display_currency) if result.display_currency else None
        )
    )


__all__ = ["router"]
