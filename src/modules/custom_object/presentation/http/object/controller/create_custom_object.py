from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.custom_object.application.field.command import CustomFieldInput
from src.modules.custom_object.application.object.command import (
    CreateCustomObjectCommand,
)
from src.modules.custom_object.domain import CustomObjectValidationError
from src.modules.custom_object.presentation.depends.application import (
    CreateCustomObjectUseCaseDep,
)
from src.modules.custom_object.presentation.http.field.responses import (
    CustomFieldResponseSchema,
)
from src.modules.custom_object.presentation.http.object.requests import (
    CreateCustomObjectRequestSchema,
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
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])


@router.post(
    "/create",
    response_model=CustomObjectResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_object(
    payload: CreateCustomObjectRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateCustomObjectUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint создания custom object."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = CreateCustomObjectCommand(
        tenant_id=EntityIdVO.from_value(tenant_id_raw),
        singular_name=payload.singular_name,
        plural_name=payload.plural_name,
        singular_label=payload.singular_label,
        plural_label=payload.plural_label,
        description=payload.description,
        fields=tuple(
            CustomFieldInput(
                field_name=field.field_name,
                type=field.type,
                label=field.label,
                description=field.description,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=dict(field.options),
                settings=dict(field.settings),
            )
            for field in payload.fields
        ),
    )

    try:
        result = await use_case(command)
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
