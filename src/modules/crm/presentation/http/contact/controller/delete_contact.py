from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends.application import DeleteContactUseCaseDep
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteContactUseCaseDep,
) -> Response:
    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        await use_case(
            DeleteContactCommand(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                contact_id=ContactIdVO.from_value(contact_id),
            )
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
