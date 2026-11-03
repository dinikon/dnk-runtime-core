from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseValueError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO


@dataclass(frozen=True, slots=True)
class Warehouse:
    """Самостоятельная карточка склада с административной активностью без локаций и остатков."""

    id: WarehouseIdVO
    code: WarehouseCodeVO
    name: WarehouseNameVO
    is_active: bool

    @classmethod
    def create(
        cls,
        *,
        identifier: WarehouseIdVO,
        code: WarehouseCodeVO,
        name: WarehouseNameVO,
    ) -> Self:
        """Создаёт активную карточку склада из явно переданных значений."""
        return cls.restore(identifier=identifier, code=code, name=name, is_active=True)

    @classmethod
    def restore(
        cls,
        *,
        identifier: WarehouseIdVO,
        code: WarehouseCodeVO,
        name: WarehouseNameVO,
        is_active: bool,
    ) -> Self:
        """Восстанавливает полный состав с проверкой значений и сохранением идентичности."""
        warehouse = cls(identifier, code, name, is_active)
        warehouse._validate()
        return warehouse

    def rename(self, name: WarehouseNameVO) -> Self:
        """Возвращает склад с новым названием и прежними ID, кодом и активностью."""
        return self._with_changes(name=name)

    def change_code(self, code: WarehouseCodeVO) -> Self:
        """Возвращает склад с новым пользовательским кодом и прежней идентичностью."""
        return self._with_changes(code=code)

    def activate(self) -> Self:
        """Разрешает использование склада, допуская повторную активацию."""
        return self._with_changes(is_active=True)

    def deactivate(self) -> Self:
        """Административно блокирует склад, допуская повторную деактивацию."""
        return self._with_changes(is_active=False)

    def ensure_available(self) -> None:
        """Проверяет собственное состояние и разрешение использовать активный склад."""
        self._validate()
        if not self.is_active:
            raise WarehouseInactiveError(
                "Неактивный склад недоступен для использования."
            )

    def _with_changes(self, **changes: object) -> Self:
        """Проверяет новый экземпляр целиком, сохраняя исходный склад при отказе."""
        warehouse = replace(self, **changes)
        warehouse._validate()
        return warehouse

    def _validate(self) -> None:
        """Требует собственные типизированные значения и настоящий bool активности."""
        if (
            not isinstance(self.id, WarehouseIdVO)
            or not isinstance(self.code, WarehouseCodeVO)
            or not isinstance(self.name, WarehouseNameVO)
            or type(self.is_active) is not bool
        ):
            raise InvalidWarehouseValueError(
                "Нужны типизированные ID, код, название и bool активности склада."
            )
