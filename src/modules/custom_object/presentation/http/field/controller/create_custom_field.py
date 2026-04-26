from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.custom_object.application.field.command import (
    AddCustomFieldCommand,
    CustomFieldInput,
)
from src.modules.custom_object.domain import (
    CustomObjectFieldNotFoundError,
    CustomObjectNotFoundError,
    CustomObjectValidationError,
)
from src.modules.custom_object.presentation.depends.application import (
    AddCustomFieldUseCaseDep,
)
from src.modules.custom_object.presentation.http.field.requests import (
    CreateCustomFieldRequestSchema,
)
from src.modules.custom_object.presentation.http.field.responses import (
    CustomFieldResponseSchema,
)
from src.modules.custom_object.presentation.http.object.responses import (
    CustomObjectResponseSchema,
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


@router.post("/fields/create", response_model=CustomObjectResponseSchema)
async def create_custom_field(
    payload: CreateCustomFieldRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: AddCustomFieldUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint добавления custom field."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            AddCustomFieldCommand(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                field=CustomFieldInput(
                    field_name=payload.field.field_name,
                    type=payload.field.type,
                    label=payload.field.label,
                    description=payload.field.description,
                    is_nullable=payload.field.is_nullable,
                    default_value=payload.field.default_value,
                    options=dict(payload.field.options),
                    settings=dict(payload.field.settings),
                ),
            )
        )
    except (CustomObjectNotFoundError, CustomObjectFieldNotFoundError) as exc:
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

    return CustomObjectResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        singular_name=result.singular_name,
        plural_name=result.plural_name,
        singular_label=result.singular_label,
        plural_label=result.plural_label,
        description=result.description,
        kind=result.kind,
        fields=[
            CustomFieldResponseSchema(
                id=field.id,
                field_name=field.field_name,
                label=field.label,
                description=field.description,
                type=field.type,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=field.options,
                kind=field.kind,
            )
            for field in result.fields
        ],
    )


__all__ = ["router"]
