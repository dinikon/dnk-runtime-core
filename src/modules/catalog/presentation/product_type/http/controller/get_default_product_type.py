from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
)
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.product_type.query.get_default_product_type.query import (
    GetDefaultProductTypeQuery,
)
from src.modules.catalog.presentation.product_type.depends import (
    GetDefaultProductTypeHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.response.get_default_product_type import (
    GetDefaultProductTypeResponse,
)


async def get_default_product_type(
    context: AuthenticatedRequestContextDep,
    handler: GetDefaultProductTypeHandlerDep,
    locale: str,
) -> GetDefaultProductTypeResponse:
    """Читает установленную фиксированную схему контента."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetDefaultProductTypeQuery(
                EntityIdVO.from_value(principal.tenant_id), locale
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    return GetDefaultProductTypeResponse.model_validate(transport_value(result))
