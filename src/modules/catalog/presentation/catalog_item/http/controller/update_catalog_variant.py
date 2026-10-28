from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogConflictError,
    CatalogNotFoundError,
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_variant.command import (
    UpdateCatalogVariantCommand,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_item.command import (
    UpdateCatalogItemContent,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    UpdateCatalogVariantHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.request.update_catalog_variant import (
    UpdateCatalogVariantRequest,
)
from src.modules.catalog.presentation.catalog_item.http.response.update_catalog_variant import (
    UpdateCatalogVariantResponse,
)


async def update_catalog_variant(
    context: AuthenticatedRequestContextDep,
    handler: UpdateCatalogVariantHandlerDep,
    item_id: UUID,
    variant_id: UUID,
    payload: UpdateCatalogVariantRequest,
    locale: str | None = None,
) -> UpdateCatalogVariantResponse:
    """Явно преобразует PATCH и ошибки конкретных разделов в HTTP-контракт."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    field = "sku"
    try:
        sku = SkuCodeVO(payload.sku) if payload.sku is not None else None
        field = "price_specification"
        price = (
            payload.price_specification.to_vo() if payload.price_specification else None
        )
        field = "stock"
        stock = payload.stock.to_vo() if payload.stock else None
        field = "weight"
        weight = payload.weight.to_vo() if payload.weight else None
        field = "dimensions"
        dimensions = payload.dimensions.to_vo() if payload.dimensions else None
        field = "gallery"
        gallery = payload.gallery.to_entity() if payload.gallery else None
    except (CatalogError, ValueError, ArithmeticError) as exc:
        raise HTTPException(
            422, {"errors": [{"field": field, "message": str(exc)}]}
        ) from exc
    try:
        result = await handler.execute(
            UpdateCatalogVariantCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                variant_id=CatalogItemIdVO(variant_id),
                fields=frozenset(payload.model_fields_set),
                locale=locale,
                status=payload.status,
                sku=sku,
                virtual=payload.virtual,
                price_specification=price,
                stock=stock,
                weight=weight,
                dimensions=dimensions,
                content=(
                    UpdateCatalogItemContent(
                        payload.content.expected_schema_version, payload.content.values
                    )
                    if payload.content
                    else None
                ),
                gallery=gallery,
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogDependencyUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except CatalogError as exc:
        status = 409 if isinstance(exc, CatalogConflictError) else 422
        raise HTTPException(
            status,
            {
                "message": str(exc),
                "errors": [
                    {"field": field, "message": str(exc)} for field in exc.fields
                ],
            },
        ) from exc
    except IntegrityError as exc:
        original = getattr(exc.orig, "__cause__", None) or exc.orig
        constraint = getattr(original, "constraint_name", None)
        if constraint == "uq_catalog_item_sku":
            raise HTTPException(
                409,
                {"errors": [{"field": "sku", "message": "Этот SKU уже используется."}]},
            ) from exc
        raise HTTPException(409, {"message": "Конфликт используемой ссылки."}) from exc
    return UpdateCatalogVariantResponse(id=result.id)
