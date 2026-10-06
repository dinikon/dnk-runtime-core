from dataclasses import dataclass

from src.modules.catalog.domain.product_type.aggregate import ProductTypeContentBlock


@dataclass(frozen=True, slots=True)
class CreateProductTypeCommand:
    code: str
    translations: dict[str, str]
    blocks: tuple[ProductTypeContentBlock, ...]
