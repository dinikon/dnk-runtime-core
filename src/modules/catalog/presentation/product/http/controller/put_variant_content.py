from uuid import UUID
from fastapi import HTTPException

from src.modules.catalog.application.product.command.put_variant_content.command import (
    PutVariantContentCommand,
)
from src.modules.catalog.domain.product_type.error import (
    ProductTypeConflictError,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    InvalidProductLocaleError,
    ProductLocaleUnavailableError,
    ProductNotFoundError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.presentation.product.depends import PutVariantContentHandlerDep
from src.modules.catalog.presentation.product.http.request.put_variant_content import (
    PutVariantContentRequest,
)
from src.modules.catalog.presentation.product.http.response.put_variant_content import (
    PutVariantContentResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_variant_content(
    product_id: UUID,
    variant_id: UUID,
    locale: str,
    payload: PutVariantContentRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutVariantContentHandlerDep,
) -> PutVariantContentResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutVariantContentCommand(
                ProductIdVO.from_value(product_id),
                VariantIdVO.from_value(variant_id),
                EntityIdVO.from_value(context.principal.user_id),
                locale,
                payload.schema_version,
                payload.blocks,
            )
        )
    except (
        InvalidProductContentError,
        InvalidProductLocaleError,
        ProductLocaleUnavailableError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ProductNotFoundError, ProductVariantNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except ProductTypeConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return PutVariantContentResponse.from_dto(result)
