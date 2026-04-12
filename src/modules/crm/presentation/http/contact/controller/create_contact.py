from __future__ import annotations

import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.contact.command.create_contact_command import (
    CreateContactCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends.application import CreateContactUseCaseDep
from src.modules.crm.presentation.http.contact.requests import (
    CreateContactRequestSchema,
)
from src.modules.crm.presentation.http.contact.responses import (
    ContactResponseSchema,
)
from src.modules.runtime_data import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.post(
    "",
    response_model=ContactResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    payload: CreateContactRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateContactUseCaseDep,
) -> ContactResponseSchema:
    """HTTP endpoint создания контакта текущего tenant.

    Endpoint берет tenant_id из principal, формирует application command и
    переводит доменные/runtime ошибки в соответствующие HTTP status codes.
    """

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = CreateContactCommand(
        tenant_id=EntityIdVO.from_value(tenant_id_raw),
        contact_id=ContactIdVO.from_value(uuid6.uuid7()),
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        status=payload.status,
        tags=tuple(payload.tags),
    )

    try:
        result = await use_case(command)
    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (RuntimeDataValidationError, RuntimeDataFilterError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ContactResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        last_name=result.last_name,
        first_name=result.first_name,
        middle_name=result.middle_name,
        status=result.status,
        tags=result.tags,
    )


__all__ = ["router"]
