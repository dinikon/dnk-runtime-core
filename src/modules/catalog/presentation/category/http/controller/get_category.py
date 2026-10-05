from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.category.query.get_category.query import (
    GetCategoryQuery,
)
from src.modules.catalog.domain.category.error import (
    CategoryNotFoundError,
    InvalidCategoryError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.presentation.category.depends import GetCategoryHandlerDep
from src.modules.catalog.presentation.category.http.context import (
    require_category_context,
)
from src.modules.catalog.presentation.category.http.response.get_category import (
    GetCategoryResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_category(
    category_id: UUID,
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: GetCategoryHandlerDep,
) -> GetCategoryResponse:
    require_category_context(context)
    try:
        result = await handler.execute(
            GetCategoryQuery(
                CategoryIdVO.from_value(category_id), CategoryLocaleVO(locale)
            )
        )
    except InvalidCategoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    except CategoryNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetCategoryResponse.from_dto(result)
