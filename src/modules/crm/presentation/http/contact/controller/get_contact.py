from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.contact.query.get_contact_query import GetContactQuery
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.presentation.depends.application import GetContactUseCaseDep
from src.modules.crm.presentation.http.contact.responses import ContactResponseSchema
from src.modules.runtime_data.domain.error import (
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
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


@router.get(
    "/{contact_id}",
    response_model=ContactResponseSchema,
)
async def get_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetContactUseCaseDep,
) -> ContactResponseSchema:
    """HTTP endpoint получения одного контакта текущего tenant."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            GetContactQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                contact_id=ContactIdVO.from_value(contact_id),
            )
        )
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
