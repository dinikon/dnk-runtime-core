from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.inventory.application.category.query.list_categories_query import (
    ListCategoriesQuery,
)
from src.modules.inventory.domain.category.error import CategoryNotFoundError
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.presentation.depends.application import (
    ListCategoriesUseCaseDep,
)
from src.modules.inventory.presentation.http.category.responses import (
    CategoryResponseSchema,
    ListCategoriesResponseSchema,
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

router = APIRouter(prefix="/inventory/categories", tags=["inventory-categories"])


@router.get(
    "",
    response_model=ListCategoriesResponseSchema,
)
async def list_categories(
    context: AuthenticatedRequestContextDep,
    use_case: ListCategoriesUseCaseDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    parent_category_id: UUID | None = Query(default=None),
) -> ListCategoriesResponseSchema:
    """HTTP endpoint списка категорий текущего tenant с limit/offset пагинацией."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListCategoriesQuery(
                tenant_id=EntityIdVO.from_value(tenant_id_raw),
                limit=limit,
                offset=offset,
                parent_category_id=(
                    None
                    if parent_category_id is None
                    else CategoryIdVO.from_value(parent_category_id)
                ),
            )
        )
    except CategoryNotFoundError as exc:
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

    return ListCategoriesResponseSchema(
        items=[
            CategoryResponseSchema(
                id=category.id,
                created_at=category.created_at,
                updated_at=category.updated_at,
                name=category.name,
                parent_category_id=category.parent_category_id,
            )
            for category in result
        ],
        limit=limit,
        offset=offset,
        count=len(result),
    )


__all__ = ["router"]
