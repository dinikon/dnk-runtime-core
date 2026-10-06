import html
import re
from dataclasses import dataclass
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
    ContentBlockType,
)
from src.modules.catalog.domain.product.error import InvalidProductContentError


@dataclass(frozen=True, slots=True)
class ContentBlockRule:
    block_id: ContentBlockIdVO
    code: str
    type: ContentBlockType
    required: bool


class ProductContentPolicy:
    """Чистые правила заполнения локализованных блоков Product и Variant."""

    @staticmethod
    def validate(
        rules: tuple[ContentBlockRule, ...], blocks: dict[str, str]
    ) -> dict[ContentBlockIdVO, str]:
        allowed = {item.code: item for item in rules}
        if set(blocks) - set(allowed):
            raise InvalidProductContentError(
                "Content block is not assigned to this scope."
            )
        values: dict[ContentBlockIdVO, str] = {}
        for code, value in blocks.items():
            if not isinstance(value, str):
                raise InvalidProductContentError("Content value must be a string.")
            rule = allowed[code]
            if rule.type is ContentBlockType.RICH_TEXT:
                visible = html.unescape(re.sub(r"<[^>]*>", "", value)).strip()
                if not visible:
                    if rule.required:
                        raise InvalidProductContentError(
                            "Required content block is empty."
                        )
                    continue
                if len(value) > 65_535:
                    raise InvalidProductContentError("Rich text value is too long.")
            else:
                if not value.strip():
                    if rule.required:
                        raise InvalidProductContentError(
                            "Required content block is empty."
                        )
                    continue
                limit = 255 if code == "title" else 4096
                if len(value) > limit:
                    raise InvalidProductContentError("Text value is too long.")
            values[rule.block_id] = value
        if any(item.required and item.block_id not in values for item in rules):
            raise InvalidProductContentError("Required content block is missing.")
        return values
