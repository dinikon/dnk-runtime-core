from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.inventory.application.category.command import UpdateCategoryCommand
from src.modules.inventory.domain.category.error import CategoryNotFoundError
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.presentation.depends.application import (
    UpdateCategoryUseCaseDep,
)
from src.modules.inventory.presentation.http.category.requests import (
    UpdateCategoryRequestSchema,
)
from src.modules.inventory.presentation.http.category.responses import (
    CategoryResponseSchema,
)
from src.modules.runtime_data import (
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

router = APIRouter(prefix="/inventory/categories", tags=["inventory-categories"])


@router.put(
    "/{category_id}",
    response_model=CategoryResponseSchema,
)
async def update_category(
    category_id: UUID,
    payload: UpdateCategoryRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateCategoryUseCaseDep,
) -> CategoryResponseSchema:
    """HTTP endpoint обновления категории текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = UpdateCategoryCommand(
        tenant_id=EntityIdVO.from_value(tenant_id_raw),
        category_id=CategoryIdVO.from_value(category_id),
        name=payload.name,
        parent_category_id=(
            None
            if payload.parent_category_id is None
            else CategoryIdVO.from_value(payload.parent_category_id)
        ),
    )

    try:
        result = await use_case(command)
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

    return CategoryResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        name=result.name,
        parent_category_id=result.parent_category_id,
    )


__all__ = ["router"]
