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
from src.modules.catalog.application.product.command.set_variant_properties.command import (
    SetVariantPropertiesCommand,
)
from src.modules.catalog.presentation.product.depends import (
    SetVariantPropertiesHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.set_variant_properties import (
    SetVariantPropertiesRequest,
)
from src.modules.catalog.presentation.product.http.response.set_variant_properties import (
    SetVariantPropertiesResponse,
)


async def set_variant_properties(
    context: AuthenticatedRequestContextDep,
    handler: SetVariantPropertiesHandlerDep,
    payload: SetVariantPropertiesRequest,
    product_id: UUID,
    variant_id: UUID,
) -> SetVariantPropertiesResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = SetVariantPropertiesCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            product_id=ProductIdVO.from_value(product_id),
            expected_revision=payload.expected_revision,
            variant_id=VariantIdVO.from_value(variant_id),
            virtual=payload.virtual,
            downloadable=payload.downloadable,
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
    return SetVariantPropertiesResponse(**asdict(result))
