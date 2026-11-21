from dataclasses import dataclass

from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO


@dataclass(frozen=True, slots=True)
class PackagingTypeSnapshot:
    """Неизменяемые настройки тары для проверки назначения товару без чужого агрегата."""

    id: PackagingTypeIdVO
    code: PackagingCodeVO
    name: PackagingNameVO
    is_active: bool
