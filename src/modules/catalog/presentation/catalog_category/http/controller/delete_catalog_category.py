from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_category.depends import (
    DeleteCatalogCategoryHandlerDep,
)
from src.modules.catalog.application.catalog_category.command.delete_catalog_category.command import (
    DeleteCatalogCategoryCommand,
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


async def delete_catalog_category(
    context: AuthenticatedRequestContextDep,
    handler: DeleteCatalogCategoryHandlerDep,
    category_id: UUID,
) -> None:
    """Удаляет свободный узел дерева."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteCatalogCategoryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                category_id=CatalogCategoryIdVO(category_id),
            )
        )
    except CatalogNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except CatalogConflictError as error:
        raise HTTPException(409, str(error)) from error
    except CatalogError as error:
        raise HTTPException(422, str(error)) from error
