from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.inventory.presentation.depends.application import (
    DescribeCategoryFieldsUseCaseDep,
)
from src.modules.inventory.presentation.http.category.responses import (
    CategoryFieldDescriptionResponseSchema,
    CategoryFieldOptionResponseSchema,
    CategoryFieldsResponseSchema,
    CategoryObjectDescriptionResponseSchema,
)
from src.modules.schema_registry.domain.error import (
    DataSourceNotFoundError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared import DomainError

router = APIRouter(prefix="/inventory/categories", tags=["inventory-categories"])


@router.post(
    "/fields",
    response_model=CategoryFieldsResponseSchema,
)
async def describe_category_fields(
    context: AuthenticatedRequestContextDep,
    use_case: DescribeCategoryFieldsUseCaseDep,
) -> CategoryFieldsResponseSchema:
    """HTTP endpoint получения описания модели product_category для tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(EntityIdVO.from_value(tenant_id_raw))
    except (
        DataSourceNotFoundError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return CategoryFieldsResponseSchema(
        object=CategoryObjectDescriptionResponseSchema(
            id=result.object_description.id,
            singular_label=result.object_description.singular_label,
            plural_label=result.object_description.plural_label,
            description=result.object_description.description,
            kind=result.object_description.kind,
        ),
        fields=[
            CategoryFieldDescriptionResponseSchema(
                id=field.id,
                field_name=field.field_name,
                label=field.label,
                description=field.description,
                type=field.type,
                kind=field.kind,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=[
                    CategoryFieldOptionResponseSchema(
                        value=option.value,
                        label=option.label,
                    )
                    for option in field.options
                ],
            )
            for field in result.fields
        ],
    )


__all__ = ["router"]
