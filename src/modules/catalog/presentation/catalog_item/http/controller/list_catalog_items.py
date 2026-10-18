from datetime import datetime
from fastapi import HTTPException, Query
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
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.query import (
    ListCatalogItemsQuery,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    ListCatalogItemsHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.list_catalog_items import (
    ListCatalogItemsResponse,
)


async def list_catalog_items(
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogItemsHandlerDep,
    locale: str,
    status: CatalogItemStatus | None = None,
    search: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    as_of: datetime | None = None,
) -> ListCatalogItemsResponse:
    """Преобразует HTTP вход list_catalog_items в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListCatalogItemsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                locale=locale,
                status=status,
                search=search,
                offset=offset,
                limit=limit,
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
    return ListCatalogItemsResponse.model_validate(transport_value(result))
