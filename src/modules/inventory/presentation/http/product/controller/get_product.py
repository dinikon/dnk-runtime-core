from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.inventory.application.product.query.get_product_query import (
    GetProductQuery,
)
from src.modules.inventory.domain.product.error import ProductNotFoundError
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.inventory.presentation.depends.application import GetProductUseCaseDep
from src.modules.inventory.presentation.http.product.responses import (
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
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/inventory/products", tags=["inventory-products"])


@router.get(
    "/{product_id}",
    response_model=ProductResponseSchema,
)
async def get_product(
    product_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetProductUseCaseDep,
) -> ProductResponseSchema:
    """HTTP endpoint получения одного товара текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            GetProductQuery(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                product_id=ProductIdVO.from_value(product_id),
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

    return ProductResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        sku=result.sku,
        product_name=result.product_name,
        description=result.description,
        category_id=result.category_id,
    )


__all__ = ["router"]
