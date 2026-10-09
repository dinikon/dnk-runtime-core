from dataclasses import asdict
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
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.application.product.command.change_product_type.command import (
    ChangeProductTypeCommand,
)
from src.modules.catalog.presentation.product.depends import ChangeProductTypeHandlerDep
from src.modules.catalog.presentation.product.http.request.change_product_type import (
    ChangeProductTypeRequest,
)
from src.modules.catalog.presentation.product.http.response.change_product_type import (
    ChangeProductTypeResponse,
)


async def change_product_type(
    context: AuthenticatedRequestContextDep,
    handler: ChangeProductTypeHandlerDep,
    payload: ChangeProductTypeRequest,
    product_id: UUID,
) -> ChangeProductTypeResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = ChangeProductTypeCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            product_id=ProductIdVO.from_value(product_id),
            expected_revision=payload.expected_revision,
            product_type_id=ProductTypeIdVO.from_value(payload.product_type_id),
        )
        result = await handler.execute(command)
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogDependencyUnavailableError as exc:
        raise HTTPException(422, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"23505", "23503"}:
            raise HTTPException(
                409, "Код уже существует или объект используется."
            ) from exc
        raise
    return ChangeProductTypeResponse(**asdict(result))
