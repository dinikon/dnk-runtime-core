from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_category.depends import (
    CreateCatalogCategoryHandlerDep,
)
from src.modules.catalog.application.catalog_category.command.create_catalog_category.command import (
    CreateCatalogCategoryCommand,
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
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.presentation.catalog_category.http.request.create_catalog_category import (
    CreateCatalogCategoryRequest,
)
from src.modules.catalog.presentation.catalog_category.http.response.create_catalog_category import (
    CreateCatalogCategoryResponse,
)


async def create_catalog_category(
    context: AuthenticatedRequestContextDep,
    handler: CreateCatalogCategoryHandlerDep,
    payload: CreateCatalogCategoryRequest,
) -> CreateCatalogCategoryResponse:
    """Создаёт узел дерева с названием на выбранном языке."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateCatalogCategoryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                parent_id=(
                    CatalogCategoryIdVO(payload.parent_id)
                    if payload.parent_id
                    else None
                ),
                locale=LocaleVO(payload.locale),
                name=payload.name,
            )
        )
    except CatalogNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except CatalogConflictError as error:
        raise HTTPException(409, str(error)) from error
    except CatalogError as error:
        raise HTTPException(422, str(error)) from error
    return CreateCatalogCategoryResponse(id=result.id)
