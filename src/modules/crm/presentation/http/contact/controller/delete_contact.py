from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.shared import EntityIdVO
from src.modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.presentation.depends.application import DeleteContactUseCaseDep
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    contact_id: UUID,
    _: AuthenticatedRequestContextDep,
    use_case: DeleteContactUseCaseDep,
) -> Response:
    try:
        await use_case(
            DeleteContactCommand(contact_id=EntityIdVO.from_value(contact_id))
        )
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
