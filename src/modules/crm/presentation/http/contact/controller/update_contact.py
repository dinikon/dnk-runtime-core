from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.contact.command.rename_contact_command import (
    RenameContactCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO
from src.modules.crm.presentation.depends.application import UpdateContactUseCaseDep
from src.modules.crm.presentation.http.contact.requests import (
    UpdateContactRequestSchema,
)
from src.modules.crm.presentation.http.contact.responses import ContactResponseSchema
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.put(
    "/{contact_id}",
    response_model=ContactResponseSchema,
)
async def update_contact(
    contact_id: UUID,
    payload: UpdateContactRequestSchema,
    _: AuthenticatedRequestContextDep,
    use_case: UpdateContactUseCaseDep,
) -> ContactResponseSchema:
    command = RenameContactCommand(
        contact_id=ContactIdVO.from_value(contact_id),
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
    )

    try:
        result = await use_case(command)
    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
