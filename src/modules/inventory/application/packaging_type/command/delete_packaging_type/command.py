from dataclasses import dataclass

from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class DeletePackagingTypeCommand:
    """Передаёт идентификатор удаляемого типа тары без клиентской версии."""

    packaging_type_id: PackagingTypeIdVO
