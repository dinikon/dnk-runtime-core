from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.broadcast.application.broadcast.command import CreateBroadcastCommand
from src.modules.broadcast.presentation.depends.application import (
    CreateBroadcastUseCaseDep,
)
from src.modules.broadcast.presentation.http.broadcast.requests import (
    CreateBroadcastRequestSchema,
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

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


@router.post(
    "",
    response_model=BroadcastResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_broadcast(
    payload: CreateBroadcastRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateBroadcastUseCaseDep,
) -> BroadcastResponseSchema:
    """HTTP endpoint создания broadcast текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = CreateBroadcastCommand(
        tenant_id=tenant_id_raw,
        title=payload.title,
        description=payload.description,
    )

    try:
        result = await use_case(command)
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

    return BroadcastResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        title=result.title,
        description=result.description,
        status=result.status,
    )


__all__ = ["router"]
