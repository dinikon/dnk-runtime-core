from uuid import UUID
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
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.application.product_type.command.delete_product_type.command import (
    DeleteProductTypeCommand,
)
from src.modules.catalog.presentation.product_type.depends import (
    DeleteProductTypeHandlerDep,
)


async def delete_product_type(
    context: AuthenticatedRequestContextDep,
    handler: DeleteProductTypeHandlerDep,
    product_type_id: UUID,
    expected_revision: int = Query(ge=1),
) -> None:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = DeleteProductTypeCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            product_type_id=ProductTypeIdVO.from_value(product_type_id),
            expected_revision=expected_revision,
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
    return None
