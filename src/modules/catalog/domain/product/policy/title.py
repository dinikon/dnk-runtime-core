from collections.abc import Mapping
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope


class VariantTitlePolicy:
    """Разрешает Title выбранной locale без копирования или наследования описания."""

    @staticmethod
    def resolve(
        title_block_id: str | None,
        product_content: Mapping[str, str] | None,
        variant_content: Mapping[str, str] | None,
    ) -> tuple[str | None, ContentScope | None]:
        """Отсутствующий ключ наследуется; пустая строка остаётся override."""
        if title_block_id is None:
            return None, None
        if variant_content is not None and title_block_id in variant_content:
            return variant_content[title_block_id], ContentScope.VARIANT
        if product_content is not None and title_block_id in product_content:
            return product_content[title_block_id], ContentScope.PRODUCT
        return None, None
