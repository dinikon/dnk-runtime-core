from collections.abc import Callable
from typing import TypeVar
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
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogConflictError,
    CatalogNotFoundError,
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_item.command import (
    UpdateCatalogItemCommand,
    UpdateCatalogItemContent,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    UpdateCatalogItemHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.request.update_catalog_item import (
    UpdateCatalogItemRequest,
)
from src.modules.catalog.presentation.catalog_item.http.response.update_catalog_item import (
    UpdateCatalogItemResponse,
)

T = TypeVar("T")


def converted(field: str, action: Callable[[], T]) -> T:
    """Привязывает ошибку преобразования VO к явно указанному HTTP-полю."""
    try:
        return action()
    except (CatalogError, ValueError, ArithmeticError) as exc:
        raise HTTPException(
            422, {"errors": [{"field": field, "message": str(exc)}]}
        ) from exc


async def update_catalog_item(
    context: AuthenticatedRequestContextDep,
    handler: UpdateCatalogItemHandlerDep,
    item_id: UUID,
    payload: UpdateCatalogItemRequest,
    locale: str | None = None,
) -> UpdateCatalogItemResponse:
    """Явно преобразует PATCH и ошибки конкретных разделов в HTTP-контракт."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateCatalogItemCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                fields=frozenset(payload.model_fields_set),
                locale=locale,
                status=payload.status,
                sku=(
                    converted("sku", lambda: SkuCodeVO(payload.sku))
                    if payload.sku is not None
                    else None
                ),
                virtual=payload.virtual,
                price_specification=(
                    converted("price_specification", payload.price_specification.to_vo)
                    if payload.price_specification
                    else None
                ),
                stock=(
                    converted("stock", payload.stock.to_vo) if payload.stock else None
                ),
                weight=(
                    converted("weight", payload.weight.to_vo)
                    if payload.weight
                    else None
                ),
                dimensions=(
                    converted("dimensions", payload.dimensions.to_vo)
                    if payload.dimensions
                    else None
                ),
                content=(
                    UpdateCatalogItemContent(
                        payload.content.expected_schema_version, payload.content.values
                    )
                    if payload.content
                    else None
                ),
                gallery=(
                    converted("gallery", payload.gallery.to_entity)
                    if payload.gallery
                    else None
                ),
                attributes=(
                    converted(
                        "attributes",
                        lambda: tuple(v.to_vo() for v in payload.attributes),
                    )
                    if payload.attributes is not None
                    else None
                ),
                metadata=(
                    converted(
                        "metadata",
                        lambda: tuple(v.to_entity() for v in payload.metadata),
                    )
                    if payload.metadata is not None
                    else None
                ),
                category_ids=(
                    tuple(CategoryIdVO(i) for i in payload.category_ids)
                    if payload.category_ids is not None
                    else None
                ),
                primary_category_id=(
                    CategoryIdVO(payload.primary_category_id)
                    if payload.primary_category_id
                    else None
                ),
                tag_ids=(
                    tuple(TagIdVO(i) for i in payload.tag_ids)
                    if payload.tag_ids is not None
                    else None
                ),
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
        # Constraint identity is safe; SQL values and driver messages never leave this boundary.
        original = getattr(exc.orig, "__cause__", None) or exc.orig
        constraint = getattr(original, "constraint_name", None)
        if constraint == "uq_catalog_item_sku":
            raise HTTPException(
                409,
                {"errors": [{"field": "sku", "message": "Этот SKU уже используется."}]},
            ) from exc
        raise HTTPException(409, {"message": "Конфликт используемой ссылки."}) from exc
    return UpdateCatalogItemResponse(id=result.id)
