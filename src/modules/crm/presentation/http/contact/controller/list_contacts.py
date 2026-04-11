from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)
from src.modules.crm.presentation.depends.application import ListContactsUseCaseDep
from src.modules.crm.presentation.http.contact.responses import (
    ContactResponseSchema,
    ListContactsResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.get(
    "",
    response_model=ListContactsResponseSchema,
)
async def list_contacts(
    context: AuthenticatedRequestContextDep,
    use_case: ListContactsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListContactsResponseSchema:
    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListContactsQuery(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                limit=limit,
                offset=offset,
            )
        )
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ListContactsResponseSchema(
        items=[
            ContactResponseSchema(
                id=contact.id,
                created_at=contact.created_at,
                updated_at=contact.updated_at,
                last_name=contact.last_name,
                first_name=contact.first_name,
                middle_name=contact.middle_name,
            )
            for contact in result
        ],
        limit=limit,
        offset=offset,
        count=len(result),
    )


__all__ = ["router"]
