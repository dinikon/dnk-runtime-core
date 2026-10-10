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
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.application.tag.command.put_tag_translation.command import (
    PutTagTranslationCommand,
)
from src.modules.catalog.presentation.tag.depends import (
    PutTagTranslationHandlerDep,
)
from src.modules.catalog.presentation.tag.http.response.put_tag_translation import (
    PutTagTranslationResponse,
)
from src.modules.catalog.presentation.tag.http.request.put_tag_translation import (
    PutTagTranslationRequest,
)


async def put_tag_translation(
    context: AuthenticatedRequestContextDep,
    handler: PutTagTranslationHandlerDep,
    tag_id: UUID,
    locale: str,
    payload: PutTagTranslationRequest,
) -> PutTagTranslationResponse:
    """Преобразует явный HTTP-контракт put_tag_translation и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutTagTranslationCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                tag_id=TagIdVO.from_value(tag_id),
                expected_revision=payload.expected_revision,
                locale=locale,
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
    return PutTagTranslationResponse(**asdict(result))
