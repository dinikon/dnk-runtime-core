from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.product_type.command.delete_product_type.command import (
    DeleteProductTypeCommand,
)
from src.modules.catalog.domain.product_type.error import (
    ProductTypeNotFoundError,
    ProductTypeConflictError,
    InvalidProductTypeError,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.presentation.product_type.depends import (
    DeleteProductTypeHandlerDep,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_type(
    type_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteProductTypeHandlerDep,
) -> None:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteProductTypeCommand(ProductTypeIdVO.from_value(type_id))
        )
    except ProductTypeNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ProductTypeConflictError, IntegrityError) as exc:
        raise HTTPException(409, str(exc)) from exc
