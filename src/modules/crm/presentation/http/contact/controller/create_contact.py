from __future__ import annotations

import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.contact.command.create_contact_command import (
    CreateContactCommand,
)
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO
from src.modules.crm.presentation.depends.application import CreateContactUseCaseDep
from src.modules.crm.presentation.http.contact.requests import (
    CreateContactRequestSchema,
)
from src.modules.crm.presentation.http.contact.responses import (
    ContactResponseSchema,
)
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.depends.clock import ClockDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.post(
    "",
    response_model=ContactResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    payload: CreateContactRequestSchema,
    _: AuthenticatedRequestContextDep,
    clock: ClockDep,
    use_case: CreateContactUseCaseDep,
) -> ContactResponseSchema:
    command = CreateContactCommand(
        contact_id=ContactIdVO.from_value(uuid6.uuid7()),
        now=clock.now(),
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
    )

    try:
        result = await use_case(command)
    except (TypeError, ValueError) as exc:
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
