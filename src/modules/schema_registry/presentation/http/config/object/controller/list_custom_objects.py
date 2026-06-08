from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.schema_registry.application.config.object.query import (
    ListCustomObjectsQuery,
)
from src.modules.schema_registry.presentation.depends.config import (
    ListCustomObjectsUseCaseDep,
)
from src.modules.schema_registry.presentation.http.config.field.responses import (
    CustomFieldResponseSchema,
)
from src.modules.schema_registry.presentation.http.config.object.responses import (
    CustomObjectResponseSchema,
    ListCustomObjectsResponseSchema,
)
from src.modules.schema_registry.domain.error import (
    PhysicalSchemaNotFoundError,
    RuntimeObjectDescriptorError,
    SchemaRegistryError,
    SchemaRegistryMetadataInconsistentError,
    UnsupportedSchemaBackendError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared import DomainError

router = APIRouter(prefix="/config/objects", tags=["config"])


@router.post("/list", response_model=ListCustomObjectsResponseSchema)
async def list_custom_objects(
    context: AuthenticatedRequestContextDep,
    use_case: ListCustomObjectsUseCaseDep,
) -> ListCustomObjectsResponseSchema:
    """HTTP endpoint списка custom objects."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListCustomObjectsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
            )
        )
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
    except (SchemaRegistryError, DomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListCustomObjectsResponseSchema(
        items=[
            CustomObjectResponseSchema(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                singular_name=item.singular_name,
                plural_name=item.plural_name,
                singular_label=item.singular_label,
                plural_label=item.plural_label,
                description=item.description,
                kind=item.kind,
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
                    for field in item.fields
                ],
            )
            for item in result
        ],
        count=len(result),
    )


__all__ = ["router"]
