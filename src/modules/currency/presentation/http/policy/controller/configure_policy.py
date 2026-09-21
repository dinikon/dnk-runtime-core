from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.policy.command.configure_currency_policy_command import (
    ConfigureCurrencyPolicy,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.currency.domain.policy.error import (
    CurrencyConflict,
    CurrencyPolicyNotConfigured,
)
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.presentation.depends.application import (
    ConfigureCurrencyPolicyUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.policy.requests.configure_policy_request import (
    ConfigureRequest,
)
from src.modules.currency.presentation.http.policy.responses.policy_response import (
    PolicyResponse,
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
    "/policy", dependencies=[Depends(require_csrf)], response_model=PolicyResponse
)
async def configure_policy(
    context: AuthenticatedRequestContextDep,
    use_case: ConfigureCurrencyPolicyUseCaseDep,
    payload: ConfigureRequest,
):
    """HTTP entrypoint for configure policy."""
    if "currency.manage_policy" not in permissions(context):
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
        return PolicyResponse.from_dto(
            await use_case(
                ConfigureCurrencyPolicy(
                    tenant,
                    actor,
                    CurrencyPolicy(
                        Code(payload.default_transaction_currency),
                        ProviderCode(payload.provider_code),
                        RateDatePolicy(payload.rate_date_policy),
                        RoundingMode(payload.rounding_mode),
                        payload.allow_cross_rate,
                        Code(payload.bridge_currency),
                        payload.business_timezone,
                        1,
                        (
                            Code(payload.default_display_currency)
                            if payload.default_display_currency
                            else None
                        ),
                    ),
                    payload.expected_version,
                )
            )
        )
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyConflict as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyDisabled as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyPolicyNotConfigured as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except InvalidCurrencyCodeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except CurrencyError as exc:
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
