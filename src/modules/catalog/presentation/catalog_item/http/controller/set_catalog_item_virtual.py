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
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_virtual.command import (
    SetCatalogItemVirtualCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    SetCatalogItemVirtualHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_virtual import (
    SetCatalogItemVirtualResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_item_virtual import (
    SetCatalogItemVirtualRequest,
)


async def set_catalog_item_virtual(
    context: AuthenticatedRequestContextDep,
    handler: SetCatalogItemVirtualHandlerDep,
    item_id: UUID,
    payload: SetCatalogItemVirtualRequest,
) -> SetCatalogItemVirtualResponse:
    """Преобразует HTTP вход set_catalog_item_virtual в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetCatalogItemVirtualCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                virtual=payload.virtual,
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
    return SetCatalogItemVirtualResponse.model_validate(transport_value(result))
