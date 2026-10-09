from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO


@dataclass(frozen=True, slots=True)
class DeleteVariantContentCommand:
    """Вход сценария delete_variant_content; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    variant_id: VariantIdVO
    locale: str
