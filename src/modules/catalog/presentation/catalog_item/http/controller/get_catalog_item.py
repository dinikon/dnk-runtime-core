from uuid import UUID
from datetime import datetime
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
from src.modules.catalog.application.catalog_item.query.get_catalog_item.query import (
    GetCatalogItemQuery,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    GetCatalogItemHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.get_catalog_item import (
    GetCatalogItemResponse,
)


async def get_catalog_item(
    context: AuthenticatedRequestContextDep,
    handler: GetCatalogItemHandlerDep,
    item_id: UUID,
    locale: str,
    as_of: datetime | None = None,
) -> GetCatalogItemResponse:
    """Преобразует HTTP вход get_catalog_item в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetCatalogItemQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                item_id=CatalogItemIdVO(item_id),
                locale=locale,
                as_of=as_of,
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
    return GetCatalogItemResponse.model_validate(transport_value(result))
