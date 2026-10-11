from uuid import UUID
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
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_item_variants.query import (
    ListCatalogItemVariantsQuery,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    ListCatalogItemVariantsHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.list_catalog_item_variants import (
    ListCatalogItemVariantsResponse,
)


async def list_catalog_item_variants(
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogItemVariantsHandlerDep,
    root_id: UUID,
    locale: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    as_of: datetime | None = None,
) -> ListCatalogItemVariantsResponse:
    """Преобразует HTTP вход list_catalog_item_variants в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListCatalogItemVariantsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                root_id=CatalogItemIdVO(root_id),
                locale=locale,
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
    return ListCatalogItemVariantsResponse.model_validate(transport_value(result))
