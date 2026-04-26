from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.custom_object.application.object.query import ListCustomObjectsQuery
from src.modules.custom_object.presentation.depends.application import (
    ListCustomObjectsUseCaseDep,
)
from src.modules.custom_object.presentation.http.field.responses import (
    CustomFieldResponseSchema,
)
from src.modules.custom_object.presentation.http.object.responses import (
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
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])


@router.post("/list", response_model=ListCustomObjectsResponseSchema)
async def list_custom_objects(
    context: AuthenticatedRequestContextDep,
    use_case: ListCustomObjectsUseCaseDep,
) -> ListCustomObjectsResponseSchema:
    """HTTP endpoint списка custom objects."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListCustomObjectsQuery(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
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
