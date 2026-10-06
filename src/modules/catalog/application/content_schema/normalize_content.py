import html
import re
from typing import Protocol
from uuid import UUID

from src.modules.catalog.application.content_schema.contracts import (
    ProductTypeSchemaDTO,
)
from src.modules.catalog.application.content_schema.service import (
    SchemaConflictError,
    SchemaValidationError,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope


class RichTextSanitizerPort(Protocol):
    def clean(self, value: str) -> str: ...


def normalize_content(
    schema: ProductTypeSchemaDTO,
    *,
    scope: ContentScope,
    version: int,
    blocks: dict[str, str],
    sanitizer: RichTextSanitizerPort,
) -> dict[UUID, str]:
    """Проверяет значения по размещению блока, а не по его определению."""
    if schema.schema_version != version:
        raise SchemaConflictError("Product type schema version changed.")
    allowed = {item.code: item for item in schema.blocks if item.scope is scope}
    if set(blocks) - set(allowed):
        raise SchemaValidationError("Content block is not assigned to this scope.")
    values: dict[UUID, str] = {}
    for code, value in blocks.items():
        if not isinstance(value, str):
            raise SchemaValidationError("Content value must be a string.")
        item = allowed[code]
        cleaned = (
            sanitizer.clean(value)
            if item.type is ContentBlockType.RICH_TEXT
            else value.strip()
        )
        if item.type is ContentBlockType.RICH_TEXT:
            visible = html.unescape(re.sub(r"<[^>]*>", "", cleaned)).strip()
            if not visible:
                if item.required:
                    raise SchemaValidationError("Required content block is empty.")
                continue
            if len(cleaned) > 65_535:
                raise SchemaValidationError("Rich text value is too long.")
        else:
            if not cleaned:
                if item.required:
                    raise SchemaValidationError("Required content block is empty.")
                continue
            limit = 255 if code == "title" else 4096
            if len(cleaned) > limit:
                raise SchemaValidationError("Text value is too long.")
        values[item.block_id] = cleaned
    if any(item.required and item.block_id not in values for item in allowed.values()):
        raise SchemaValidationError("Required content block is missing.")
    return values


def content_by_code(
    schema: ProductTypeSchemaDTO, scope: ContentScope, values: dict[UUID, str]
) -> dict[str, str]:
    return {
        item.code: values[item.block_id]
        for item in schema.blocks
        if item.scope is scope and item.block_id in values
    }
