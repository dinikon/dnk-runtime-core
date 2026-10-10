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
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.application.attribute.option_input import AttributeOptionInput
from src.modules.catalog.application.attribute.command.replace_attribute_options.command import (
    ReplaceAttributeOptionsCommand,
)
from src.modules.catalog.presentation.attribute.depends import (
    ReplaceAttributeOptionsHandlerDep,
)
from src.modules.catalog.presentation.attribute.http.response.replace_attribute_options import (
    ReplaceAttributeOptionsResponse,
)
from src.modules.catalog.presentation.attribute.http.request.replace_attribute_options import (
    ReplaceAttributeOptionsRequest,
)


async def replace_attribute_options(
    context: AuthenticatedRequestContextDep,
    handler: ReplaceAttributeOptionsHandlerDep,
    attribute_id: UUID,
    locale: str,
    payload: ReplaceAttributeOptionsRequest,
) -> ReplaceAttributeOptionsResponse:
    """Преобразует явный HTTP-контракт replace_attribute_options и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ReplaceAttributeOptionsCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                attribute_id=AttributeIdVO.from_value(attribute_id),
                expected_revision=payload.expected_revision,
                locale=locale,
                options=tuple(
                    AttributeOptionInput(
                        o.code,
                        o.label,
                        (
                            None
                            if o.option_id is None
                            else AttributeOptionIdVO.from_value(o.option_id)
                        ),
                    )
                    for o in payload.options
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
    return ReplaceAttributeOptionsResponse(**asdict(result))
