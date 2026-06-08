from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.custom_object.application.record.command import CustomRecordByIdCommand
from src.modules.custom_object.domain import (
    CustomObjectNotFoundError,
    CustomObjectRecordNotFoundError,
    CustomObjectValidationError,
)
from src.modules.custom_object.presentation.depends.application import (
    GetCustomRecordUseCaseDep,
)
from src.modules.custom_object.presentation.http.record.requests import (
    CustomRecordByIdRequestSchema,
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
from src.modules.shared import DomainError

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])


@router.post("/records/detail", response_model=CustomRecordResponseSchema)
async def get_custom_record(
    payload: CustomRecordByIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: GetCustomRecordUseCaseDep,
) -> CustomRecordResponseSchema:
    """HTTP endpoint чтения custom-object record."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            CustomRecordByIdCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                row_id=payload.row_id,
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
