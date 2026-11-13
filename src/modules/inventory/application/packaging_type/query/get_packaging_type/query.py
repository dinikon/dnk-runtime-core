from dataclasses import dataclass

from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class GetPackagingTypeQuery:
    """Передаёт ID карточки типа тары внутри текущего tenant."""

    packaging_type_id: PackagingTypeIdVO
