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
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.application.content_block.command.update_content_block.command import (
    UpdateContentBlockCommand,
)
from src.modules.catalog.presentation.content_block.depends import (
    UpdateContentBlockHandlerDep,
)
from src.modules.catalog.presentation.content_block.http.request.update_content_block import (
    UpdateContentBlockRequest,
)
from src.modules.catalog.presentation.content_block.http.response.update_content_block import (
    UpdateContentBlockResponse,
)


async def update_content_block(
    context: AuthenticatedRequestContextDep,
    handler: UpdateContentBlockHandlerDep,
    payload: UpdateContentBlockRequest,
    content_block_id: UUID,
) -> UpdateContentBlockResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = UpdateContentBlockCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            content_block_id=ContentBlockIdVO.from_value(content_block_id),
            expected_revision=payload.expected_revision,
            locale=payload.locale,
            label=payload.label,
            value_type=payload.value_type,
        )
        result = await handler.execute(command)
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogDependencyUnavailableError as exc:
        raise HTTPException(422, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"23505", "23503"}:
            raise HTTPException(
                409, "Код уже существует или объект используется."
            ) from exc
        raise
    return UpdateContentBlockResponse(**asdict(result))
