from typing import Any

from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)


class PackagingTypeMapper:
    """Преобразует ORM-модель и агрегат без SQL и бизнес-проверок."""

    @staticmethod
    def to_domain(model: PackagingTypeModel) -> PackagingType:
        """Восстанавливает полный агрегат через Domain-фабрику с сохранённым ID."""
        return PackagingType.restore(
            identifier=PackagingTypeIdVO.from_value(model.id),
            code=PackagingCodeVO(model.code),
            name=PackagingNameVO(model.name),
            is_active=model.is_active,
        )

    @staticmethod
    def to_insert_values(packaging_type: PackagingType) -> dict[str, Any]:
        """Извлекает ID и настройки, сохраняя регистр доменного кода."""
        return dict(
            id=packaging_type.id.uuid,
            code=packaging_type.code.value,
            name=packaging_type.name.value,
            is_active=packaging_type.is_active,
        )

    @staticmethod
    def to_update_values(packaging_type: PackagingType) -> dict[str, Any]:
        """Подготавливает только редактируемые значения без первичного ключа."""
        values = PackagingTypeMapper.to_insert_values(packaging_type)
        del values["id"]
        return values
