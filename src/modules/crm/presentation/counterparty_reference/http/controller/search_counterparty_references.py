from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.crm.presentation.counterparty_reference.depends import (
    SearchCounterpartyReferencesHandlerDep,
)
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.query import (
    SearchCounterpartyReferencesQuery,
)
from src.modules.crm.presentation.counterparty_reference.http.response.search_counterparty_references import (
    SearchCounterpartyReferencesResponse,
)


async def search_counterparty_references(
    model_key: CounterpartyModelKey,
    context: AuthenticatedRequestContextDep,
    handler: SearchCounterpartyReferencesHandlerDep,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> SearchCounterpartyReferencesResponse:
    """Читает страницу выбранного типа контрагентов текущего tenant."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        SearchCounterpartyReferencesQuery(model_key, search, offset, limit)
    )
    return SearchCounterpartyReferencesResponse.from_dto(result)
