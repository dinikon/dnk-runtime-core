from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.contact.query.get_contact_query import GetContactQuery
from src.modules.crm.domain.contact.service import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO
from src.modules.crm.presentation.depends.application import GetContactUseCaseDep
from src.modules.crm.presentation.http.contact.responses import ContactResponseSchema
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.get(
    "/{contact_id}",
    response_model=ContactResponseSchema,
)
async def get_contact(
    contact_id: UUID,
    _: AuthenticatedRequestContextDep,
    use_case: GetContactUseCaseDep,
) -> ContactResponseSchema:
    try:
        result = await use_case(
            GetContactQuery(contact_id=ContactIdVO.from_value(contact_id))
        )
    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ContactResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        last_name=result.last_name,
        first_name=result.first_name,
        middle_name=result.middle_name,
    )


__all__ = ["router"]
