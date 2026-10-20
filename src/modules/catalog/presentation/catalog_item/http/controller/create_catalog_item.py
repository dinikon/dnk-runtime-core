from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
    CreateCatalogItemTranslation,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
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
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.command import (
    CreateCatalogItemCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    CreateCatalogItemHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.create_catalog_item import (
    CreateCatalogItemResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.create_catalog_item import (
    CreateCatalogItemRequest,
)


async def create_catalog_item(
    context: AuthenticatedRequestContextDep,
    handler: CreateCatalogItemHandlerDep,
    payload: CreateCatalogItemRequest,
) -> CreateCatalogItemResponse:
    """Преобразует HTTP вход create_catalog_item в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateCatalogItemCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                product=CreateCatalogItemValues(
                    product_type_code=payload.product_type_code,
                    virtual=payload.virtual,
                    status=payload.status,
                    sku=payload.sku,
                    price_specification=(
                        payload.price_specification.to_vo()
                        if payload.price_specification
                        else None
                    ),
                    stock=(
                        payload.stock.to_vo()
                        if payload.stock is not None
                        else StockSpecificationVO()
                    ),
                    weight=payload.weight.to_vo() if payload.weight else None,
                    dimensions=(
                        payload.dimensions.to_vo() if payload.dimensions else None
                    ),
                    translations={
                        code: CreateCatalogItemTranslation(
                            value.values, value.expected_schema_version
                        )
                        for code, value in payload.translations.items()
                    },
                    galleries={
                        code: value.to_entity()
                        for code, value in payload.galleries.items()
                    },
                ),
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(422, "Некорректное значение.") from exc
    except IntegrityError as exc:
        raise HTTPException(
            409, "Конфликт уникального кода или используемой ссылки."
        ) from exc
    return CreateCatalogItemResponse.model_validate(transport_value(result))
