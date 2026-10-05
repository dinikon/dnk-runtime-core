from fastapi import HTTPException

from src.modules.catalog.application.product.command.create_product.command import (
    CreateProductCommand,
    CreateProductContent,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    InvalidProductLocaleError,
    ProductIdentifierAlreadyExistsError,
    ProductLocaleUnavailableError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.presentation.product.depends import CreateProductHandlerDep
from src.modules.catalog.presentation.product.http.request.create_product import (
    CreateProductRequest,
)
from src.modules.catalog.presentation.product.http.response.create_product import (
    CreateProductResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_product(
    payload: CreateProductRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateProductHandlerDep,
) -> CreateProductResponse:
    """Создаёт товар без подмены tenant и аудита."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateProductCommand(
                actor_id=EntityIdVO.from_value(principal.user_id),
                sku_id=payload.sku_id,
                contents=tuple(
                    CreateProductContent(
                        locale=item.locale,
                        name=item.name,
                        description=item.description,
                    )
                    for item in payload.contents
                ),
            )
        )
    except (
        InvalidProductContentError,
        InvalidProductLocaleError,
        ProductLocaleUnavailableError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProductSkuNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ProductIdentifierAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateProductResponse.from_dto(result)
