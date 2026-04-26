from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.custom_object.application.object.command import (
    DeleteCustomObjectCommand,
)
from src.modules.custom_object.domain import (
    CustomObjectNotFoundError,
    CustomObjectValidationError,
)
from src.modules.custom_object.presentation.depends.application import (
    DeleteCustomObjectUseCaseDep,
)
from src.modules.custom_object.presentation.http.object.requests import (
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
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_object(
    payload: ObjectIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCustomObjectUseCaseDep,
) -> Response:
    """HTTP endpoint hard delete custom object."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        await use_case(
            DeleteCustomObjectCommand(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
            )
        )
    except CustomObjectNotFoundError as exc:
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
    except (CustomObjectValidationError, SchemaRegistryError, DomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
