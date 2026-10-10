from dataclasses import asdict
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.application.category.command.move_category.command import (
    MoveCategoryCommand,
)
from src.modules.catalog.presentation.category.depends import (
    MoveCategoryHandlerDep,
)
from src.modules.catalog.presentation.category.http.response.move_category import (
    MoveCategoryResponse,
)
from src.modules.catalog.presentation.category.http.request.move_category import (
    MoveCategoryRequest,
)


async def move_category(
    context: AuthenticatedRequestContextDep,
    handler: MoveCategoryHandlerDep,
    category_id: UUID,
    payload: MoveCategoryRequest,
) -> MoveCategoryResponse:
    """Преобразует явный HTTP-контракт move_category и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            MoveCategoryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                category_id=CategoryIdVO.from_value(category_id),
                expected_revision=payload.expected_revision,
                parent_id=(
                    None
                    if payload.parent_id is None
                    else CategoryIdVO(payload.parent_id)
                ),
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"23505", "23503"}:
            raise HTTPException(
                409, "Код уже существует или объект используется."
            ) from exc
        raise
    return MoveCategoryResponse(**asdict(result))
