from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
    CreateVariableProductContent,
    CreateVariableVariant,
    CreateVariantSelection,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    InvalidProductLocaleError,
    InvalidProductVariantError,
    ProductIdentifierAlreadyExistsError,
    ProductLocaleUnavailableError,
    ProductOptionUnavailableError,
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
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_variable_product(
    payload: CreateVariableProductRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateVariableProductHandlerDep,
    authorization: AuthorizationServiceDep,
) -> CreateVariableProductResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="create",
        resource_type="catalog.product",
    ):
        raise HTTPException(403, "Product creation is not allowed.")
    try:
        result = await handler.execute(
            CreateVariableProductCommand(
                actor_id=EntityIdVO.from_value(principal.user_id),
                variants=tuple(
                    CreateVariableVariant(
                        sku_id=item.sku_id,
                        selections=tuple(
                            CreateVariantSelection(
                                attribute_id=selection.attribute_id,
                                option_id=selection.option_id,
                            )
                            for selection in item.selections
                        ),
                    )
                    for item in payload.variants
                ),
                contents=tuple(
                    CreateVariableProductContent(
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
        InvalidProductVariantError,
        ProductLocaleUnavailableError,
        ProductOptionUnavailableError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProductSkuNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ProductIdentifierAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateVariableProductResponse.from_dto(result)
