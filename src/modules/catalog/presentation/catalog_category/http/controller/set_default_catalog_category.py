from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_category.depends import (
    SetDefaultCatalogCategoryHandlerDep,
)
from src.modules.catalog.application.catalog_category.command.set_default_catalog_category.command import (
    SetDefaultCatalogCategoryCommand,
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
from src.modules.catalog.presentation.catalog_category.http.request.set_default_catalog_category import (
    SetDefaultCatalogCategoryRequest,
)
from src.modules.catalog.presentation.catalog_category.http.response.set_default_catalog_category import (
    SetDefaultCatalogCategoryResponse,
)


async def set_default_catalog_category(
    context: AuthenticatedRequestContextDep,
    handler: SetDefaultCatalogCategoryHandlerDep,
    payload: SetDefaultCatalogCategoryRequest,
) -> SetDefaultCatalogCategoryResponse:
    """Выбирает категорию по умолчанию для новых товаров."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetDefaultCatalogCategoryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                category_id=CatalogCategoryIdVO(payload.category_id),
            )
        )
    except CatalogNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except CatalogConflictError as error:
        raise HTTPException(409, str(error)) from error
    except CatalogError as error:
        raise HTTPException(422, str(error)) from error
    return SetDefaultCatalogCategoryResponse(id=result.id)
