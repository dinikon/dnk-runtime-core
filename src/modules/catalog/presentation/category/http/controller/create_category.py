from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from dataclasses import asdict
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
from src.modules.catalog.application.category.command.create_category.command import (
    CreateCategoryCommand,
)
from src.modules.catalog.presentation.category.depends import CreateCategoryHandlerDep
from src.modules.catalog.presentation.category.http.response.create_category import (
    CreateCategoryResponse,
)
from src.modules.catalog.presentation.category.http.request.create_category import (
    CreateCategoryRequest,
)


async def create_category(
    context: AuthenticatedRequestContextDep,
    handler: CreateCategoryHandlerDep,
    payload: CreateCategoryRequest,
) -> CreateCategoryResponse:
    """Преобразует явный HTTP-контракт create_category и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateCategoryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                locale=payload.locale,
                label=payload.label,
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
    return CreateCategoryResponse(**asdict(result))
