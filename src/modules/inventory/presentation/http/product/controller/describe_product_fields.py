from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.inventory.presentation.depends.application import (
    DescribeProductFieldsUseCaseDep,
)
from src.modules.inventory.presentation.http.product.responses import (
    ProductFieldDescriptionResponseSchema,
    ProductFieldOptionResponseSchema,
    ProductFieldsResponseSchema,
    ProductObjectDescriptionResponseSchema,
)
from src.modules.schema_registry.domain.error import (
    DataSourceNotFoundError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/inventory/products", tags=["inventory-products"])


@router.post(
    "/fields",
    response_model=ProductFieldsResponseSchema,
)
async def describe_product_fields(
    context: AuthenticatedRequestContextDep,
    use_case: DescribeProductFieldsUseCaseDep,
) -> ProductFieldsResponseSchema:
    """HTTP endpoint получения описания модели product для tenant."""

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

    return ProductFieldsResponseSchema(
        object=ProductObjectDescriptionResponseSchema(
            id=result.object_description.id,
            singular_label=result.object_description.singular_label,
            plural_label=result.object_description.plural_label,
            description=result.object_description.description,
            kind=result.object_description.kind,
        ),
        fields=[
            ProductFieldDescriptionResponseSchema(
                id=field.id,
                field_name=field.field_name,
                label=field.label,
                description=field.description,
                type=field.type,
                kind=field.kind,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=[
                    ProductFieldOptionResponseSchema(
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
