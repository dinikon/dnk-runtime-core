from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.category.command.put_category_content.command import (
    PutCategoryContentCommand,
)
from src.modules.catalog.domain.category.error import (
    CategoryLocaleUnavailableError,
    CategoryNotFoundError,
    InvalidCategoryError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.presentation.category.depends import (
    PutCategoryContentHandlerDep,
)
from src.modules.catalog.presentation.category.http.context import (
    require_category_context,
)
from src.modules.catalog.presentation.category.http.request.put_category_content import (
    PutCategoryContentRequest,
)
from src.modules.catalog.presentation.category.http.response.put_category_content import (
    PutCategoryContentResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_category_content(
    category_id: UUID,
    locale: str,
    payload: PutCategoryContentRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutCategoryContentHandlerDep,
) -> PutCategoryContentResponse:
    _, actor_id = require_category_context(context)
    try:
        result = await handler.execute(
            PutCategoryContentCommand(
                CategoryIdVO.from_value(category_id),
                EntityIdVO.from_value(actor_id),
                locale,
                payload.name,
            )
        )
    except (InvalidCategoryError, CategoryLocaleUnavailableError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except CategoryNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return PutCategoryContentResponse.from_dto(result)
