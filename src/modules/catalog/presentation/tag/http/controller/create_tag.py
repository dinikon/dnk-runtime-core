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
from src.modules.catalog.application.tag.command.create_tag.command import (
    CreateTagCommand,
)
from src.modules.catalog.presentation.tag.depends import CreateTagHandlerDep
from src.modules.catalog.presentation.tag.http.response.create_tag import (
    CreateTagResponse,
)
from src.modules.catalog.presentation.tag.http.request.create_tag import (
    CreateTagRequest,
)


async def create_tag(
    context: AuthenticatedRequestContextDep,
    handler: CreateTagHandlerDep,
    payload: CreateTagRequest,
) -> CreateTagResponse:
    """Преобразует явный HTTP-контракт create_tag и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateTagCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                locale=payload.locale,
                label=payload.label,
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
    return CreateTagResponse(**asdict(result))
