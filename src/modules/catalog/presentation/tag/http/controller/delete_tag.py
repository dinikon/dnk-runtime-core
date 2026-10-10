from uuid import UUID
from fastapi import HTTPException, Query
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
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.application.tag.command.delete_tag.command import (
    DeleteTagCommand,
)
from src.modules.catalog.presentation.tag.depends import DeleteTagHandlerDep


async def delete_tag(
    context: AuthenticatedRequestContextDep,
    handler: DeleteTagHandlerDep,
    tag_id: UUID,
    expected_revision: int = Query(ge=1),
) -> None:
    """Преобразует явный HTTP-контракт delete_tag и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            DeleteTagCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                tag_id=TagIdVO.from_value(tag_id),
                expected_revision=expected_revision,
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
    return None
