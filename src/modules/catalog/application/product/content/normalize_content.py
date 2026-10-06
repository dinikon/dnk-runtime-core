from uuid import UUID

from src.modules.catalog.application.product.port.rich_text_sanitizer import (
    RichTextSanitizerPort,
)
from src.modules.catalog.application.product_type.port.schema_reader import (
    ProductTypeSchemaDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
    ContentBlockType,
)
from src.modules.catalog.domain.product.content_policy import (
    ContentBlockRule,
    ProductContentPolicy,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.domain.product_type.error import ProductTypeConflictError


def normalize_content(
    schema: ProductTypeSchemaDTO,
    *,
    scope: ContentScope,
    version: int,
    blocks: dict[str, str],
    sanitizer: RichTextSanitizerPort,
) -> dict[UUID, str]:
    """Очищает HTML через порт и передаёт бизнес-проверки доменной политике."""
    if schema.schema_version != version:
        raise ProductTypeConflictError("Product type schema version changed.")
    assigned = {item.code: item for item in schema.blocks if item.scope is scope}
    normalized = {
        code: (
            sanitizer.clean(value)
            if code in assigned
            and assigned[code].type is ContentBlockType.RICH_TEXT
            and isinstance(value, str)
            else value.strip() if isinstance(value, str) else value
        )
        for code, value in blocks.items()
    }
    rules = tuple(
        ContentBlockRule(
            ContentBlockIdVO.from_value(item.block_id),
            item.code,
            item.type,
            item.required,
        )
        for item in assigned.values()
    )
    return {
        block_id.uuid: value
        for block_id, value in ProductContentPolicy.validate(rules, normalized).items()
    }


def content_by_code(
    schema: ProductTypeSchemaDTO, scope: ContentScope, values: dict[UUID, str]
) -> dict[str, str]:
    return {
        item.code: values[item.block_id]
        for item in schema.blocks
        if item.scope is scope and item.block_id in values
    }
