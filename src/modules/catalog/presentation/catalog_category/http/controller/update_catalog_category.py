from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_category.depends import (
    UpdateCatalogCategoryHandlerDep,
)
from src.modules.catalog.application.catalog_category.command.update_catalog_category.command import (
    UpdateCatalogCategoryCommand,
)
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogConflictError,
    CatalogNotFoundError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from uuid import UUID
from src.modules.catalog.presentation.catalog_category.http.request.update_catalog_category import (
    UpdateCatalogCategoryRequest,
)
from src.modules.catalog.presentation.catalog_category.http.response.update_catalog_category import (
    UpdateCatalogCategoryResponse,
)


async def update_catalog_category(
    context: AuthenticatedRequestContextDep,
    handler: UpdateCatalogCategoryHandlerDep,
    category_id: UUID,
    payload: UpdateCatalogCategoryRequest,
) -> UpdateCatalogCategoryResponse:
    """Изменяет переводы и положение категории за одну транзакцию."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateCatalogCategoryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                category_id=CatalogCategoryIdVO(category_id),
                parent_id=(
                    CatalogCategoryIdVO(payload.parent_id)
                    if payload.parent_id
                    else None
                ),
                move="parent_id" in payload.model_fields_set,
                translations=payload.translations,
            )
        )
    except CatalogNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except CatalogConflictError as error:
        raise HTTPException(409, str(error)) from error
    except CatalogError as error:
        raise HTTPException(422, str(error)) from error
    return UpdateCatalogCategoryResponse(id=result.id)
