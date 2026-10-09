from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
import re
from html import unescape
from collections.abc import Mapping
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.product.value_object.schema import ProductSchemaSnapshot
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope


class ProductContentPolicy:
    """Проверяет контент по снимку схемы без I/O и внешней очистки HTML."""

    @staticmethod
    def validate(
        values: Mapping[str, str], schema: ProductSchemaSnapshot, scope: ContentScope
    ) -> None:
        """Проверяет ID, типы и обязательность одного явного перевода."""
        blocks = {str(b.block_id): b for b in schema.blocks if b.scope == scope}
        if set(values) - set(blocks):
            raise InvalidCatalogValueError(
                "Контент содержит блоки вне выбранной схемы и scope."
            )
        for identifier, value in values.items():
            if not isinstance(value, str) or len(value) > 100000:
                raise InvalidCatalogValueError(
                    "Значение блока должно быть строкой до 100000 символов."
                )
        for identifier, block in blocks.items():
            value = values.get(identifier, "")
            visible = (
                unescape(re.sub(r"<[^>]*>", "", value))
                if block.value_type == ContentValueType.RICH_TEXT
                else value
            )
            if block.required and not visible.strip():
                raise InvalidCatalogValueError(
                    f"Обязательный блок {identifier} не заполнен."
                )
