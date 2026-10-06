from fastapi import HTTPException

from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
)
from src.modules.catalog.application.content_schema.service import (
    SchemaNotFoundError,
    SchemaConflictError,
    SchemaValidationError,
)
from src.modules.catalog.application.product.command.create_product.command import (
    CreateProductContent,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    InvalidProductLocaleError,
    InvalidProductVariantError,
    ProductIdentifierAlreadyExistsError,
    ProductLocaleUnavailableError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.presentation.product.depends import (
    CreateVariableProductHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.create_variable_product import (
    CreateVariableProductRequest,
)
from src.modules.catalog.presentation.product.http.response.create_variable_product import (
    CreateVariableProductResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_variable_product(
    payload: CreateVariableProductRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateVariableProductHandlerDep,
) -> CreateVariableProductResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateVariableProductCommand(
                EntityIdVO.from_value(context.principal.user_id),
                tuple(payload.sku_ids),
                tuple(
                    CreateProductContent(item.locale, item.blocks)
                    for item in payload.contents
                ),
                payload.product_type_id,
                payload.schema_version,
            )
        )
    except (
        InvalidProductContentError,
        InvalidProductLocaleError,
        ProductLocaleUnavailableError,
        SchemaValidationError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ProductSkuNotFoundError, SchemaNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (
        InvalidProductVariantError,
        ProductIdentifierAlreadyExistsError,
        SchemaConflictError,
    ) as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateVariableProductResponse.from_dto(result)
