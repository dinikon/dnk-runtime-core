from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from src.modules.crm.domain.contact.service import ContactNotFoundError
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO
from src.modules.crm.presentation.depends.application import DeleteContactUseCaseDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    contact_id: UUID,
    use_case: DeleteContactUseCaseDep,
) -> Response:
    try:
        await use_case(
            DeleteContactCommand(contact_id=ContactIdVO.from_value(contact_id))
        )
    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
