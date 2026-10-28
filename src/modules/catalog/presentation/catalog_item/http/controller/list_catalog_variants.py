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
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogConflictError,
    CatalogNotFoundError,
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_variants.query import (
    ListCatalogVariantsQuery,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    ListCatalogVariantsHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.list_catalog_variants import (
    ListCatalogVariantsResponse,
)


async def list_catalog_variants(
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogVariantsHandlerDep,
    item_id: UUID,
    locale: str,
    offset: int = 0,
    limit: int = 25,
) -> ListCatalogVariantsResponse:
    """Читает принадлежащие родителю позиции через конкретный Query Handler."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListCatalogVariantsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                item_id=CatalogItemIdVO(item_id),
                locale=locale,
                offset=offset,
                limit=limit,
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogDependencyUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(
            409 if isinstance(exc, CatalogConflictError) else 422,
            {
                "message": str(exc),
                "errors": [
                    {"field": field, "message": str(exc)} for field in exc.fields
                ],
            },
        ) from exc
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(422, "Некорректное значение.") from exc
    except IntegrityError as exc:
        raise HTTPException(
            409,
            {
                "message": "Конфликт SKU или используемой ссылки.",
                "errors": [{"field": "sku", "message": "Этот SKU уже используется."}],
            },
        ) from exc
    return ListCatalogVariantsResponse.model_validate(transport_value(result))
