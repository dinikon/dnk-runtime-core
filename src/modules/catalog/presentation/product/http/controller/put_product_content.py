from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product.command.put_product_content.command import (
    PutProductContentCommand,
)
from src.modules.catalog.application.content_schema.service import (
    SchemaConflictError,
    SchemaValidationError,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    InvalidProductLocaleError,
    ProductLocaleUnavailableError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.presentation.product.depends import PutProductContentHandlerDep
from src.modules.catalog.presentation.product.http.request.put_product_content import (
    PutProductContentRequest,
)
from src.modules.catalog.presentation.product.http.response.put_product_content import (
    PutProductContentResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_product_content(
    product_id: UUID,
    locale: str,
    payload: PutProductContentRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutProductContentHandlerDep,
) -> PutProductContentResponse:
    """Добавляет либо полностью заменяет один перевод карточки."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutProductContentCommand(
                product_id=ProductIdVO.from_value(product_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                locale=locale,
                schema_version=payload.schema_version,
                blocks=payload.blocks,
            )
        )
    except (
        InvalidProductContentError,
        InvalidProductLocaleError,
        ProductLocaleUnavailableError,
        SchemaValidationError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except SchemaConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return PutProductContentResponse.from_dto(result)
