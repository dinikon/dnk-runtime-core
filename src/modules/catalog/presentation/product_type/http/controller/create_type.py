from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.product_type.command.create_product_type.command import (
    CreateProductTypeCommand,
)
from src.modules.catalog.domain.content_block.error import ContentBlockNotFoundError
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.aggregate import ProductTypeContentBlock
from src.modules.catalog.domain.product_type.error import (
    ProductTypeNotFoundError,
    ProductTypeConflictError,
    InvalidProductTypeError,
)
from src.modules.catalog.presentation.product_type.depends import (
    CreateProductTypeHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.request.create_type import (
    CreateTypeRequest,
)
from src.modules.catalog.presentation.product_type.http.response.create_type import (
    CreateTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def create_type(
    payload: CreateTypeRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateProductTypeHandlerDep,
) -> CreateTypeResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        item = await handler.execute(
            CreateProductTypeCommand(
                payload.code,
                payload.translations,
                tuple(
                    ProductTypeContentBlock(
                        ContentBlockIdVO.from_value(item.block_id),
                        item.scope,
                        item.required,
                        item.position,
                    )
                    for item in payload.blocks
                ),
            )
        )
    except (ProductTypeNotFoundError, ContentBlockNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ProductTypeConflictError, IntegrityError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (InvalidProductTypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateTypeResponse.from_dto(item)
