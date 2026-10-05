from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.category.command.delete_category.command import (
    DeleteCategoryCommand,
)
from src.modules.catalog.domain.category.error import (
    CategoryInUseError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.presentation.category.depends import DeleteCategoryHandlerDep
from src.modules.catalog.presentation.category.http.context import (
    require_category_context,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def delete_category(
    category_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteCategoryHandlerDep,
) -> None:
    tenant_id, _ = require_category_context(context)
    try:
        await handler.execute(
            DeleteCategoryCommand(
                EntityIdVO.from_value(tenant_id), CategoryIdVO.from_value(category_id)
            )
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CategoryInUseError as exc:
        raise HTTPException(409, str(exc)) from exc
