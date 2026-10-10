from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
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
from src.modules.catalog.application.product.command.set_product_categories.command import (
    SetProductCategoriesCommand,
)
from src.modules.catalog.presentation.product.depends import (
    SetProductCategoriesHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.set_product_categories import (
    SetProductCategoriesRequest,
)
from src.modules.catalog.presentation.product.http.response.set_product_categories import (
    SetProductCategoriesResponse,
)


async def set_product_categories(
    context: AuthenticatedRequestContextDep,
    handler: SetProductCategoriesHandlerDep,
    payload: SetProductCategoriesRequest,
    product_id: UUID,
) -> SetProductCategoriesResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = SetProductCategoriesCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            product_id=ProductIdVO.from_value(product_id),
            expected_revision=payload.expected_revision,
            category_ids=tuple(CategoryIdVO(i) for i in payload.category_ids),
            primary_category_id=(
                None
                if payload.primary_category_id is None
                else CategoryIdVO(payload.primary_category_id)
            ),
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
    return SetProductCategoriesResponse(**asdict(result))
