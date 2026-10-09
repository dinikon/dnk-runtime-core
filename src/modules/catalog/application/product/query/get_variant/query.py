from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO


@dataclass(frozen=True, slots=True)
class GetVariantQuery:
    """Вход сценария get_variant; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    product_id: ProductIdVO
    variant_id: VariantIdVO
    locale: str
