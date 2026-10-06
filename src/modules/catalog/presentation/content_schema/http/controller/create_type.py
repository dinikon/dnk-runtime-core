from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.aggregate import ProductTypeContentBlock
from src.modules.catalog.presentation.content_schema.depends import (
    ContentSchemaServiceDep,
)
from src.modules.catalog.presentation.content_schema.http.context import (
    require_tenant,
    raise_schema_http_error,
)
from src.modules.catalog.presentation.content_schema.http.request.create_type import (
    CreateTypeRequest,
)
from src.modules.catalog.presentation.content_schema.http.response.product_type import (
    ProductTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def create_type(
    payload: CreateTypeRequest,
    context: AuthenticatedRequestContextDep,
    service: ContentSchemaServiceDep,
) -> ProductTypeResponse:
    require_tenant(context)
    try:
        blocks = tuple(
            ProductTypeContentBlock(
                ContentBlockIdVO.from_value(item.block_id),
                item.scope,
                item.required,
                item.position,
            )
            for item in payload.blocks
        )
        return ProductTypeResponse.from_dto(
            await service.create_type(payload.code, payload.translations, blocks)
        )
    except Exception as exc:
        raise_schema_http_error(exc)
