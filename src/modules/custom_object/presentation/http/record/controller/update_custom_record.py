from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.custom_object.application.record.command import (
    UpdateCustomRecordCommand,
)
from src.modules.custom_object.domain import (
    CustomObjectNotFoundError,
    CustomObjectRecordNotFoundError,
    CustomObjectValidationError,
)
from src.modules.custom_object.presentation.depends.application import (
    UpdateCustomRecordUseCaseDep,
)
from src.modules.custom_object.presentation.http.record.requests import (
    UpdateCustomRecordRequestSchema,
)
from src.modules.custom_object.presentation.http.record.responses import (
    CustomRecordResponseSchema,
)
from src.modules.runtime_data.domain.error import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    PhysicalSchemaNotFoundError,
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryError,
    SchemaRegistryMetadataInconsistentError,
    UnsupportedSchemaBackendError,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])


@router.patch("/records/update", response_model=CustomRecordResponseSchema)
@router.put("/records/update", response_model=CustomRecordResponseSchema)
async def update_custom_record(
    payload: UpdateCustomRecordRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateCustomRecordUseCaseDep,
) -> CustomRecordResponseSchema:
    """HTTP endpoint обновления custom-object record."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            UpdateCustomRecordCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                row_id=payload.row_id,
                values=payload.values,
            )
        )
    except (
        CustomObjectNotFoundError,
        CustomObjectRecordNotFoundError,
        RuntimeObjectNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        PhysicalSchemaNotFoundError,
        SchemaRegistryMetadataInconsistentError,
        UnsupportedSchemaBackendError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (
        CustomObjectValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
        SchemaRegistryError,
        DomainError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return CustomRecordResponseSchema(
        object_id=result.object_id,
        row_id=result.row_id,
        values=dict(result.values),
    )


__all__ = ["router"]
