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
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.value_object.block_link import (
    ProductTypeContentBlock,
)
from src.modules.catalog.application.product_type.command.create_product_type.command import (
    CreateProductTypeCommand,
)
from src.modules.catalog.presentation.product_type.depends import (
    CreateProductTypeHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.request.create_product_type import (
    CreateProductTypeRequest,
)
from src.modules.catalog.presentation.product_type.http.response.create_product_type import (
    CreateProductTypeResponse,
)


async def create_product_type(
    context: AuthenticatedRequestContextDep,
    handler: CreateProductTypeHandlerDep,
    payload: CreateProductTypeRequest,
) -> CreateProductTypeResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        command = CreateProductTypeCommand(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            actor_id=EntityIdVO.from_value(principal.user_id),
            code=payload.code,
            locale=payload.locale,
            label=payload.label,
            blocks=tuple(
                ProductTypeContentBlock(
                    ContentBlockIdVO(b.block_id), b.scope, b.required, b.position
                )
                for b in payload.blocks
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
    return CreateProductTypeResponse(**asdict(result))
