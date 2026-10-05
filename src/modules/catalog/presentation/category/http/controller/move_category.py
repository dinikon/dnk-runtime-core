from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.category.command.move_category.command import (
    MoveCategoryCommand,
)
from src.modules.catalog.domain.category.error import (
    CategoryCycleError,
    CategoryNotFoundError,
    InvalidCategoryError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.presentation.category.depends import MoveCategoryHandlerDep
from src.modules.catalog.presentation.category.http.context import (
    require_category_context,
)
from src.modules.catalog.presentation.category.http.request.move_category import (
    MoveCategoryRequest,
)
from src.modules.catalog.presentation.category.http.response.move_category import (
    MoveCategoryResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def move_category(
    category_id: UUID,
    payload: MoveCategoryRequest,
    context: AuthenticatedRequestContextDep,
    handler: MoveCategoryHandlerDep,
) -> MoveCategoryResponse:
    tenant_id, actor_id = require_category_context(context)
    try:
        result = await handler.execute(
            MoveCategoryCommand(
                EntityIdVO.from_value(tenant_id),
                CategoryIdVO.from_value(category_id),
                (
                    CategoryIdVO.from_value(payload.parent_id)
                    if payload.parent_id
                    else None
                ),
                EntityIdVO.from_value(actor_id),
            )
        )
    except InvalidCategoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    except CategoryNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CategoryCycleError as exc:
        raise HTTPException(409, str(exc)) from exc
    return MoveCategoryResponse.from_dto(result)
