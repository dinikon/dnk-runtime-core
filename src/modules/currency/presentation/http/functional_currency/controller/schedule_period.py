from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError
from uuid import uuid4
from src.modules.currency.application.functional_currency.command.schedule_functional_currency_change_command import (
    ScheduleFunctionalCurrencyChange,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyPeriodOverlap,
    FunctionalCurrencyChangeNotAllowed,
)
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.presentation.depends.application import (
    ScheduleFunctionalCurrencyChangeUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.functional_currency.requests.schedule_request import (
    ScheduleRequest,
)
from src.modules.currency.presentation.http.functional_currency.responses.period_response import (
    PeriodResponse,
)
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money_errors import InvalidCurrencyCodeError
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.post(
    "/periods",
    dependencies=[Depends(require_csrf)],
    status_code=201,
    response_model=PeriodResponse,
)
async def schedule_period(
    context: AuthenticatedRequestContextDep,
    use_case: ScheduleFunctionalCurrencyChangeUseCaseDep,
    payload: ScheduleRequest,
):
    """HTTP entrypoint for schedule period."""
    if "currency.change_functional_currency" not in permissions(context):
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
        return PeriodResponse.from_dto(
            await use_case(
                ScheduleFunctionalCurrencyChange(
                    tenant,
                    actor,
                    Code(payload.currency),
                    payload.effective_from,
                    payload.reason,
                    FunctionalCurrencyPeriodIdVO(uuid4()),
                )
            )
        )
    except CurrencyNotFound as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    except FunctionalCurrencyPeriodOverlap as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    except FunctionalCurrencyChangeNotAllowed as exc:
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
