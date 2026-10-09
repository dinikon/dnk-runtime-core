from dataclasses import asdict
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
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.application.product.command.create_simple_product.command import (
    CreateSimpleProductCommand,
)
from src.modules.catalog.presentation.product.depends import (
    CreateSimpleProductHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.create_simple_product import (
    CreateSimpleProductRequest,
)
from src.modules.catalog.presentation.product.http.response.create_simple_product import (
    CreateSimpleProductResponse,
)


async def create_simple_product(
    context: AuthenticatedRequestContextDep,
    handler: CreateSimpleProductHandlerDep,
    payload: CreateSimpleProductRequest,
) -> CreateSimpleProductResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = CreateSimpleProductCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            product_type_id=(
                None
                if payload.product_type_id is None
                else ProductTypeIdVO.from_value(payload.product_type_id)
            ),
            virtual=payload.virtual,
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
    return CreateSimpleProductResponse(**asdict(result))
