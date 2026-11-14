from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.packaging_type.error import (
    InvalidPackagingTypeError,
    PackagingTypeInUseError,
)
from src.modules.inventory.domain.packaging_type.deletion_usage import (
    PackagingTypeDeletionUsage,
)
from src.modules.inventory.domain.packaging_type.snapshot import PackagingTypeSnapshot
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO


@dataclass(frozen=True, slots=True)
class PackagingType:
    """Пользовательский форм-фактор тары, независимый от единиц учёта товара."""

    id: PackagingTypeIdVO
    code: PackagingCodeVO
    name: PackagingNameVO
    is_active: bool

    @classmethod
    def create(
        cls,
        *,
        identifier: PackagingTypeIdVO,
        code: PackagingCodeVO,
        name: PackagingNameVO,
    ) -> Self:
        """Создаёт активный тип пользовательского справочника тары."""
        return cls.restore(
            identifier=identifier,
            code=code,
            name=name,
            is_active=True,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: PackagingTypeIdVO,
        code: PackagingCodeVO,
        name: PackagingNameVO,
        is_active: bool,
    ) -> Self:
        """Восстанавливает идентичность, название, код и признак активности."""
        value = cls(identifier, code, name, is_active)
        value._validate()
        return value

    def rename(self, name: PackagingNameVO) -> Self:
        """Возвращает тип тары с новым названием и прежним ID."""
        return self._with_changes(name=name)

    def change_code(self, code: PackagingCodeVO) -> Self:
        """Возвращает тип тары с новым пользовательским кодом."""
        return self._with_changes(code=code)

    def activate(self) -> Self:
        """Разрешает новые назначения типа тары товарам."""
        return self._with_changes(is_active=True)

    def deactivate(self) -> Self:
        """Запрещает новые назначения, сохраняя идентичность исторических ссылок."""
        return self._with_changes(is_active=False)

    def ensure_can_delete(self, usage: PackagingTypeDeletionUsage) -> None:
        """Запрещает удаление при любой ссылке из ItemPackaging независимо от активности."""
        if usage.has_item_packagings:
            raise PackagingTypeInUseError(
                "Нельзя удалить тип тары: он используется в упаковках товаров. "
                "Используемый тип можно деактивировать."
            )

    def snapshot(self) -> PackagingTypeSnapshot:
        """Возвращает настройки без передачи другого корня агрегата в InventoryItem."""
        return PackagingTypeSnapshot(self.id, self.code, self.name, self.is_active)

    def _with_changes(self, **changes: object) -> Self:
        """Проверяет новый экземпляр, не меняя исходный тип тары."""
        value = replace(self, **changes)
        value._validate()
        return value

    def _validate(self) -> None:
        """Проверяет собственные значения форм-фактора тары."""
        if (
            not isinstance(self.id, PackagingTypeIdVO)
            or not isinstance(self.code, PackagingCodeVO)
            or not isinstance(self.name, PackagingNameVO)
            or type(self.is_active) is not bool
        ):
            raise InvalidPackagingTypeError(
                "Нужны типизированные ID, код, название и признак активности тары."
            )
