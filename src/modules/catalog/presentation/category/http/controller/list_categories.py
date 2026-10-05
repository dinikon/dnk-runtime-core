from fastapi import HTTPException

from src.modules.catalog.application.category.query.list_categories.query import (
    ListCategoriesQuery,
)
from src.modules.catalog.domain.category.error import InvalidCategoryError
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.presentation.category.depends import ListCategoriesHandlerDep
from src.modules.catalog.presentation.category.http.context import (
    require_category_context,
)
from src.modules.catalog.presentation.category.http.response.list_categories import (
    ListCategoryResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_categories(
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: ListCategoriesHandlerDep,
) -> list[ListCategoryResponse]:
    require_category_context(context)
    try:
        result = await handler.execute(ListCategoriesQuery(CategoryLocaleVO(locale)))
    except InvalidCategoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return [ListCategoryResponse.from_dto(item) for item in result]
