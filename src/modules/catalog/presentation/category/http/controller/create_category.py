from fastapi import HTTPException

from src.modules.catalog.application.category.command.create_category.command import (
    CreateCategoryCommand,
    CreateCategoryTranslation,
)
from src.modules.catalog.domain.category.error import (
    CategoryIdentifierAlreadyExistsError,
    CategoryNotFoundError,
    CategoryLocaleUnavailableError,
    InvalidCategoryError,
)
from src.modules.catalog.presentation.category.depends import CreateCategoryHandlerDep
from src.modules.catalog.presentation.category.http.context import (
    require_category_context,
)
from src.modules.catalog.presentation.category.http.request.create_category import (
    CreateCategoryRequest,
)
from src.modules.catalog.presentation.category.http.response.create_category import (
    CreateCategoryResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_category(
    payload: CreateCategoryRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateCategoryHandlerDep,
) -> CreateCategoryResponse:
    tenant_id, actor_id = require_category_context(context)
    try:
        result = await handler.execute(
            CreateCategoryCommand(
                tenant_id=EntityIdVO.from_value(tenant_id),
                actor_id=EntityIdVO.from_value(actor_id),
                parent_id=payload.parent_id,
                translations=tuple(
                    CreateCategoryTranslation(item.locale, item.name)
                    for item in payload.translations
                ),
            )
        )
    except (InvalidCategoryError, CategoryLocaleUnavailableError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except CategoryNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CategoryIdentifierAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateCategoryResponse.from_dto(result)
