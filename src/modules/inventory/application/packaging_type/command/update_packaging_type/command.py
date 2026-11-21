from dataclasses import dataclass

from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class UpdatePackagingTypeCommand:
    """Передаёт ID и явно изменяемые поля без подстановки defaults создания."""

    packaging_type_id: PackagingTypeIdVO
    fields: frozenset[str]
    code: str | None = None
    name: str | None = None
    is_active: bool | None = None
