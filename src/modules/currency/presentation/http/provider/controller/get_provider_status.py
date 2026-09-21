from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import OperationalError
from src.modules.currency.application.provider.query.get_provider_status_query import (
    GetProviderStatusQuery,
)
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.presentation.depends.application import (
    GetProviderStatusUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.provider.responses.provider_status_response import (
    ProviderStatusResponse,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/provider-status", response_model=ProviderStatusResponse)
async def get_provider_status(
    context: AuthenticatedRequestContextDep,
    use_case: GetProviderStatusUseCaseDep,
    provider: str = "NBU",
):
    """HTTP entrypoint for get provider status."""
    if "currency.view" not in permissions(context):
        raise HTTPException(
            403,
            {
                "code": "currency_forbidden",
                "message": "Currency permission is required.",
            },
        )
    tenant = EntityIdVO.from_value(context.principal.tenant_id)
    try:
        return ProviderStatusResponse.from_dto(
            await use_case(GetProviderStatusQuery(ProviderCode(provider)))
        )
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
