from fastapi import APIRouter, HTTPException
from src.modules.currency.application.provider.query.list_rate_sources_query import (
    ListRateSourcesQuery,
)
from src.modules.currency.presentation.depends.application import (
    ListRateSourcesUseCaseDep,
)
from src.modules.currency.presentation.http.authorization import permissions
from src.modules.currency.presentation.http.provider.responses.rate_source_response import (
    RateSourceResponse,
    ProviderCapabilitiesResponse,
)
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.get("/sources", response_model=list[RateSourceResponse])
async def list_rate_sources(
    context: AuthenticatedRequestContextDep, use_case: ListRateSourcesUseCaseDep
):
    """List sources available to the authenticated organization."""
    if "currency.view" not in permissions(context):
        raise HTTPException(
            403,
            {
                "code": "currency_forbidden",
                "message": "Currency permission is required.",
            },
        )
    sources = await use_case(ListRateSourcesQuery())
    return [
        RateSourceResponse(
            code=str(s.code),
            local=s.local,
            capabilities=ProviderCapabilitiesResponse(
                historical_rates=s.capabilities.historical_rates,
                supported_currencies=s.capabilities.supported_currencies,
                base_currency=(
                    str(s.capabilities.base_currency)
                    if s.capabilities.base_currency
                    else None
                ),
                bulk_download=s.capabilities.bulk_download,
            ),
        )
        for s in sources
    ]


__all__ = ["router"]
