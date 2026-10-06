from uuid import UUID
from fastapi import HTTPException, Response

from src.modules.catalog.application.product.command.delete_product.command import (
    DeleteProductCommand,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.presentation.product.depends import DeleteProductHandlerDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_product(
    product_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteProductHandlerDep,
) -> Response:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(DeleteProductCommand(ProductIdVO.from_value(product_id)))
    except ProductNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)
