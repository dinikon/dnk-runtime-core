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
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.application.product.command.put_variant_content.command import (
    PutVariantContentCommand,
)
from src.modules.catalog.presentation.product.depends import PutVariantContentHandlerDep
from src.modules.catalog.presentation.product.http.request.put_variant_content import (
    PutVariantContentRequest,
)
from src.modules.catalog.presentation.product.http.response.put_variant_content import (
    PutVariantContentResponse,
)


async def put_variant_content(
    context: AuthenticatedRequestContextDep,
    handler: PutVariantContentHandlerDep,
    payload: PutVariantContentRequest,
    product_id: UUID,
    variant_id: UUID,
    locale: str,
) -> PutVariantContentResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = PutVariantContentCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            product_id=ProductIdVO.from_value(product_id),
            expected_revision=payload.expected_revision,
            variant_id=VariantIdVO.from_value(variant_id),
            locale=locale,
            expected_schema_version=payload.expected_schema_version,
            values=payload.values,
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
    return PutVariantContentResponse(**asdict(result))
