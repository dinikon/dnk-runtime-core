from dataclasses import asdict
from uuid import UUID
from fastapi import HTTPException

from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.command import (
    SetCatalogItemSkuCommand,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogConflictError,
    CatalogNotFoundError,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    SetCatalogItemSkuHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.inventory_item_selection_value import (
    inventory_item_selection,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_variant_sku import (
    SetCatalogVariantSkuRequest,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_variant_sku import (
    SetCatalogVariantSkuResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def set_catalog_variant_sku(
    item_id: UUID,
    variant_id: UUID,
    payload: SetCatalogVariantSkuRequest,
    context: AuthenticatedRequestContextDep,
    handler: SetCatalogItemSkuHandlerDep,
) -> SetCatalogVariantSkuResponse:
    """Передаёт изменение варианта через корень указанной семьи Catalog."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    selection = inventory_item_selection(payload.root)
    assert selection is not None
    try:
        result = await handler.execute(
            SetCatalogItemSkuCommand(
                EntityIdVO.from_value(principal.tenant_id),
                EntityIdVO.from_value(principal.user_id),
                CatalogItemIdVO(item_id),
                selection,
                CatalogItemIdVO(variant_id),
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(
            409,
            {
                "message": str(exc),
                "errors": [
                    {"field": field, "message": str(exc)} for field in exc.fields
                ],
            },
        ) from exc
    except CatalogError as exc:
        raise HTTPException(
            422,
            {
                "message": str(exc),
                "errors": [
                    {"field": field, "message": str(exc)} for field in exc.fields
                ],
            },
        ) from exc
    return SetCatalogVariantSkuResponse(**asdict(result))
