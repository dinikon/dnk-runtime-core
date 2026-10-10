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
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.application.attribute.command.put_attribute_translation.command import (
    PutAttributeTranslationCommand,
)
from src.modules.catalog.presentation.attribute.depends import (
    PutAttributeTranslationHandlerDep,
)
from src.modules.catalog.presentation.attribute.http.response.put_attribute_translation import (
    PutAttributeTranslationResponse,
)
from src.modules.catalog.presentation.attribute.http.request.put_attribute_translation import (
    PutAttributeTranslationRequest,
)


async def put_attribute_translation(
    context: AuthenticatedRequestContextDep,
    handler: PutAttributeTranslationHandlerDep,
    attribute_id: UUID,
    locale: str,
    payload: PutAttributeTranslationRequest,
) -> PutAttributeTranslationResponse:
    """Преобразует явный HTTP-контракт put_attribute_translation и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutAttributeTranslationCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                attribute_id=AttributeIdVO.from_value(attribute_id),
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
    return PutAttributeTranslationResponse(**asdict(result))
