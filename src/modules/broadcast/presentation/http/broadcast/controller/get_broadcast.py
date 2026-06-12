from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.broadcast.application.broadcast.query import GetBroadcastQuery
from src.modules.broadcast.presentation.depends.application import (
    GetBroadcastUseCaseDep,
)
from src.modules.broadcast.presentation.http.broadcast.requests import (
    GetBroadcastRequestSchema,
)
from src.modules.broadcast.presentation.http.broadcast.responses import (
    BroadcastResponseSchema,
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
    "/broadcast/item/get",
    response_model=BroadcastResponseSchema,
)
async def get_broadcast(
    payload: GetBroadcastRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: GetBroadcastUseCaseDep,
) -> BroadcastResponseSchema:
    """HTTP endpoint чтения broadcast текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    query = GetBroadcastQuery(
        tenant_id=tenant_id_raw,
        broadcast_id=payload.id,
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

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found.",
        )

    return BroadcastResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        title=result.title,
        description=result.description,
        status=result.status,
    )


__all__ = ["router"]
