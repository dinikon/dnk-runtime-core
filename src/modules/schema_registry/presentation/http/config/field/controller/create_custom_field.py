from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.schema_registry.application.config.field.command import (
    AddCustomFieldCommand,
    CustomFieldInput,
)
from src.modules.schema_registry.domain.error import (
    FieldNotFoundError,
    ObjectNotFoundError,
    SchemaRegistryError,
)
from src.modules.schema_registry.presentation.depends.config import (
    AddCustomFieldUseCaseDep,
)
from src.modules.schema_registry.presentation.http.config.field.requests import (
    CreateCustomFieldRequestSchema,
)
from src.modules.schema_registry.presentation.http.config.field.responses import (
    CustomFieldResponseSchema,
)
from src.modules.schema_registry.presentation.http.config.object.responses import (
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
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/config/objects", tags=["config"])


@router.post("/fields/create", response_model=CustomObjectResponseSchema)
async def create_custom_field(
    payload: CreateCustomFieldRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: AddCustomFieldUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint добавления custom field."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            AddCustomFieldCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
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
    except (ObjectNotFoundError, FieldNotFoundError) as exc:
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
