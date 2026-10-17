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
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.command import (
    SetCatalogItemSkuCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    SetCatalogItemSkuHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_sku import (
    SetCatalogItemSkuResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_item_sku import (
    SetCatalogItemSkuRequest,
)


async def set_catalog_item_sku(
    context: AuthenticatedRequestContextDep,
    handler: SetCatalogItemSkuHandlerDep,
    item_id: UUID,
    payload: SetCatalogItemSkuRequest,
) -> SetCatalogItemSkuResponse:
    """Преобразует HTTP вход set_catalog_item_sku в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetCatalogItemSkuCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                sku=SkuCodeVO(payload.sku) if payload.sku is not None else None,
                expected_revision=payload.expected_revision,
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
    return SetCatalogItemSkuResponse.model_validate(transport_value(result))
