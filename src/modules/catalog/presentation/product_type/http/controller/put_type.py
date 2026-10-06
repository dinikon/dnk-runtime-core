from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.product_type.command.put_product_type.command import (
    PutProductTypeCommand,
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
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.presentation.product_type.depends import (
    PutProductTypeHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.request.put_type import (
    PutTypeRequest,
)
from src.modules.catalog.presentation.product_type.http.response.put_type import (
    PutTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def put_type(
    type_id: UUID,
    payload: PutTypeRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutProductTypeHandlerDep,
) -> PutTypeResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        item = await handler.execute(
            PutProductTypeCommand(
                ProductTypeIdVO.from_value(type_id),
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
                payload.expected_schema_version,
            )
        )
    except (ProductTypeNotFoundError, ContentBlockNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ProductTypeConflictError, IntegrityError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (InvalidProductTypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutTypeResponse.from_dto(item)
