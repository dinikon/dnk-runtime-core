from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.content_schema.service import (
    SchemaConflictError,
    SchemaNotFoundError,
)
from src.modules.catalog.application.product.command.put_product_type.command import (
    PutProductTypeCommand,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.presentation.product.depends import PutProductTypeHandlerDep
from src.modules.catalog.presentation.product.http.request.put_product_type import (
    PutProductTypeRequest,
)
from src.modules.catalog.presentation.product.http.response.put_product_type import (
    PutProductTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_product_type(
    product_id: UUID,
    payload: PutProductTypeRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutProductTypeHandlerDep,
) -> PutProductTypeResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutProductTypeCommand(
                ProductIdVO.from_value(product_id),
                ProductTypeIdVO.from_value(payload.product_type_id),
                payload.expected_schema_version,
                EntityIdVO.from_value(context.principal.user_id),
            )
        )
    except (ProductNotFoundError, SchemaNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except SchemaConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return PutProductTypeResponse.from_dto(result)
