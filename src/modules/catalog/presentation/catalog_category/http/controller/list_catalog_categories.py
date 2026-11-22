from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_category.depends import (
    ListCatalogCategoriesHandlerDep,
)
from src.modules.catalog.application.catalog_category.query.list_catalog_categories.query import (
    ListCatalogCategoriesQuery,
)
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogConflictError,
    CatalogNotFoundError,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.presentation.catalog_category.http.response.list_catalog_categories import (
    ListCatalogCategoriesResponse,
)


async def list_catalog_categories(
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogCategoriesHandlerDep,
    locale: str,
) -> ListCatalogCategoriesResponse:
    """Возвращает дерево с названиями для выбранной локали."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListCatalogCategoriesQuery(locale=LocaleVO(locale))
        )
    except CatalogNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except CatalogConflictError as error:
        raise HTTPException(409, str(error)) from error
    except CatalogError as error:
        raise HTTPException(422, str(error)) from error
    return ListCatalogCategoriesResponse.model_validate(result, from_attributes=True)
