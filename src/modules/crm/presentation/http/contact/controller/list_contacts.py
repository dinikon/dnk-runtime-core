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
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.get(
    "",
    response_model=ListContactsResponseSchema,
)
async def list_contacts(
    _: AuthenticatedRequestContextDep,
    use_case: ListContactsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListContactsResponseSchema:
    try:
        result = await use_case(ListContactsQuery(limit=limit, offset=offset))
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
