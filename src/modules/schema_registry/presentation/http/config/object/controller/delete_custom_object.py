from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.schema_registry.application.config.object.command import (
    DeleteCustomObjectCommand,
)
from src.modules.schema_registry.domain.error import ObjectNotFoundError
from src.modules.schema_registry.presentation.depends.config import (
    DeleteCustomObjectUseCaseDep,
)
from src.modules.schema_registry.presentation.http.config.object.requests import (
    ObjectIdRequestSchema,
)
from src.modules.schema_registry.domain.error import (
    PhysicalSchemaNotFoundError,
    RuntimeObjectDescriptorError,
    SchemaRegistryError,
    SchemaRegistryMetadataInconsistentError,
    UnsupportedSchemaBackendError,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared import DomainError

router = APIRouter(prefix="/config/objects", tags=["config"])


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_object(
    payload: ObjectIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCustomObjectUseCaseDep,
) -> Response:
    """HTTP endpoint hard delete custom object."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        await use_case(
            DeleteCustomObjectCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
            )
        )
    except ObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        PhysicalSchemaNotFoundError,
        RuntimeObjectDescriptorError,
        SchemaRegistryMetadataInconsistentError,
        UnsupportedSchemaBackendError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (SchemaRegistryError, SchemaRegistryError, DomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
