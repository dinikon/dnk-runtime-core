from __future__ import annotations

import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.inventory.application.product.command import CreateProductCommand
from src.modules.inventory.domain.category.error import CategoryNotFoundError
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.error import ProductNotFoundError
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.inventory.presentation.depends.application import (
    CreateProductUseCaseDep,
)
from src.modules.inventory.presentation.http.product.requests import (
    CreateProductRequestSchema,
)
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
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/inventory/products", tags=["inventory-products"])


@router.post(
    "",
    response_model=ProductResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: CreateProductRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateProductUseCaseDep,
) -> ProductResponseSchema:
    """HTTP endpoint создания товара текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = CreateProductCommand(
        tenant_id=EntityIdVO.from_value(tenant_id_raw),
        product_id=ProductIdVO.from_value(uuid6.uuid7()),
        sku=payload.sku,
        product_name=payload.product_name,
        description=payload.description,
        category_id=(
            None
            if payload.category_id is None
            else CategoryIdVO.from_value(payload.category_id)
        ),
    )

    try:
        result = await use_case(command)
    except (ProductNotFoundError, CategoryNotFoundError) as exc:
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
