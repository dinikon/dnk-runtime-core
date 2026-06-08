from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.inventory.application.product.query.list_products_query import (
    ListProductsQuery,
)
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.error import ProductNotFoundError
from src.modules.inventory.presentation.depends.application import (
    ListProductsUseCaseDep,
)
from src.modules.inventory.presentation.http.product.responses import (
    ListProductsResponseSchema,
    ProductResponseSchema,
)
from src.modules.runtime_data.domain.error import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared import DomainError

router = APIRouter(prefix="/inventory/products", tags=["inventory-products"])


@router.get(
    "",
    response_model=ListProductsResponseSchema,
)
async def list_products(
    context: AuthenticatedRequestContextDep,
    use_case: ListProductsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: UUID | None = Query(default=None),
) -> ListProductsResponseSchema:
    """HTTP endpoint списка товаров текущего tenant с limit/offset пагинацией."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListProductsQuery(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                limit=limit,
                offset=offset,
                category_id=(
                    None
                    if category_id is None
                    else CategoryIdVO.from_value(category_id)
                ),
            )
        )
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (RuntimeDataValidationError, RuntimeDataFilterError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListProductsResponseSchema(
        items=[
            ProductResponseSchema(
                id=product.id,
                created_at=product.created_at,
                updated_at=product.updated_at,
                sku=product.sku,
                product_name=product.product_name,
                description=product.description,
                category_id=product.category_id,
            )
            for product in result
        ],
        limit=limit,
        offset=offset,
        count=len(result),
    )


__all__ = ["router"]
