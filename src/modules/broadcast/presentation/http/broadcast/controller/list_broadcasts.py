from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.broadcast.application.broadcast.query import ListBroadcastsQuery
from src.modules.broadcast.presentation.depends.application import (
    ListBroadcastsUseCaseDep,
)
from src.modules.broadcast.presentation.http.broadcast.requests import (
    ListBroadcastsRequestSchema,
)
from src.modules.broadcast.presentation.http.broadcast.responses import (
    BroadcastListPaginationResponseSchema,
    BroadcastResponseSchema,
    ListBroadcastsResponseSchema,
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
from src.modules.shared import DomainError
from src.modules.shared.presentation.identity_context import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.post(
    "/broadcast/item/list",
    response_model=ListBroadcastsResponseSchema,
)
async def list_broadcasts(
    payload: ListBroadcastsRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListBroadcastsUseCaseDep,
) -> ListBroadcastsResponseSchema:
    """HTTP endpoint списка broadcasts текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    query = ListBroadcastsQuery(
        tenant_id=tenant_id_raw,
        filter_dsl=payload.filter,
        sort_dsl=payload.sort,
        limit=payload.pagination.limit,
        offset=payload.pagination.offset,
    )

    try:
        result = await use_case(query)
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
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListBroadcastsResponseSchema(
        data=[
            BroadcastResponseSchema(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                title=item.title,
                description=item.description,
                status=item.status,
            )
            for item in result.items
        ],
        pagination=BroadcastListPaginationResponseSchema(
            limit=result.limit,
            offset=result.offset,
            total=result.total,
        ),
    )


__all__ = ["router"]
