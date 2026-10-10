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
from src.modules.catalog.application.attribute.option_input import AttributeOptionInput
from src.modules.catalog.application.attribute.command.create_attribute.command import (
    CreateAttributeCommand,
)
from src.modules.catalog.presentation.attribute.depends import CreateAttributeHandlerDep
from src.modules.catalog.presentation.attribute.http.response.create_attribute import (
    CreateAttributeResponse,
)
from src.modules.catalog.presentation.attribute.http.request.create_attribute import (
    CreateAttributeRequest,
)


async def create_attribute(
    context: AuthenticatedRequestContextDep,
    handler: CreateAttributeHandlerDep,
    payload: CreateAttributeRequest,
) -> CreateAttributeResponse:
    """Преобразует явный HTTP-контракт create_attribute и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateAttributeCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                code=payload.code,
                locale=payload.locale,
                label=payload.label,
                options=tuple(
                    AttributeOptionInput(o.code, o.label) for o in payload.options
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
    return CreateAttributeResponse(**asdict(result))
