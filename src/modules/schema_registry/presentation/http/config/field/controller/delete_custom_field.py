from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.schema_registry.application.config.field.command import (
    DeleteCustomFieldCommand,
)
from src.modules.schema_registry.domain.error import (
    FieldNotFoundError,
    ObjectNotFoundError,
    SchemaRegistryError,
)
from src.modules.schema_registry.presentation.depends.config import (
    DeleteCustomFieldUseCaseDep,
)
from src.modules.schema_registry.presentation.http.config.field.requests import (
    DeleteCustomFieldRequestSchema,
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
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/config/objects", tags=["config"])


@router.delete("/fields/delete", response_model=CustomObjectResponseSchema)
async def delete_custom_field(
    payload: DeleteCustomFieldRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCustomFieldUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint удаления custom field."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            DeleteCustomFieldCommand(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                field_id=RuntimeFieldIdVO.from_value(payload.field_id),
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
