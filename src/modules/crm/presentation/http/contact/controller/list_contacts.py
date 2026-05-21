from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.presentation.depends.application import ListContactsUseCaseDep
from src.modules.crm.presentation.http.contact.requests import (
    ContactSearchRequestSchema,
)
from src.modules.crm.presentation.http.contact.responses import (
    ContactResponseSchema,
    ContactSearchPaginationResponseSchema,
    ContactSearchResponseSchema,
    ListContactsResponseSchema,
)
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
    """HTTP endpoint списка контактов текущего tenant с limit/offset пагинацией."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListContactsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                limit=limit,
                offset=offset,
                sort_dsl=(
                    {"field": "created_at", "direction": "asc"},
                    {"field": "id", "direction": "asc"},
                ),
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

    return ListContactsResponseSchema(
        items=[_contact_response(contact) for contact in result.items],
        limit=limit,
        offset=offset,
        count=len(result.items),
    )


@router.post(
    "/search",
    response_model=ContactSearchResponseSchema,
)
async def search_contacts(
    payload: ContactSearchRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListContactsUseCaseDep,
) -> ContactSearchResponseSchema:
    """HTTP endpoint поиска контактов текущего tenant по runtime-owned DSL."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListContactsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                filter_dsl=payload.filter,
                sort_dsl=payload.sort,
                limit=payload.pagination.limit,
                offset=payload.pagination.offset,
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

    return ContactSearchResponseSchema(
        data=[_contact_response(contact) for contact in result.items],
        pagination=ContactSearchPaginationResponseSchema(
            limit=result.limit,
            offset=result.offset,
            total=result.total,
        ),
    )


def _contact_response(contact) -> ContactResponseSchema:
    return ContactResponseSchema(
        id=contact.id,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        last_name=contact.last_name,
        first_name=contact.first_name,
        middle_name=contact.middle_name,
        status=contact.status,
        tags=contact.tags,
    )


__all__ = ["router"]
