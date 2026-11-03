from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.policy.default_storage_location import (
    DefaultStorageLocationPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseValueError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO


@dataclass(frozen=True, slots=True)
class Warehouse:
    """Карточка склада с активностью и основной локацией без коллекций адресов и остатков."""

    id: WarehouseIdVO
    code: WarehouseCodeVO
    name: WarehouseNameVO
    is_active: bool
    default_storage_location_id: StockLocationIdVO | None

    @classmethod
    def create(
        cls,
        *,
        identifier: WarehouseIdVO,
        code: WarehouseCodeVO,
        name: WarehouseNameVO,
    ) -> Self:
        """Создаёт активную карточку склада из явно переданных значений."""
        return cls.restore(
            identifier=identifier,
            code=code,
            name=name,
            is_active=True,
            default_storage_location_id=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: WarehouseIdVO,
        code: WarehouseCodeVO,
        name: WarehouseNameVO,
        is_active: bool,
        default_storage_location_id: StockLocationIdVO | None,
    ) -> Self:
        """Восстанавливает полный состав с проверкой значений и сохранением идентичности."""
        warehouse = cls(identifier, code, name, is_active, default_storage_location_id)
        warehouse._validate()
        return warehouse

    def snapshot(self) -> WarehouseSnapshot:
        """Возвращает идентичность, активность и текущую ссылку на основную локацию."""
        self._validate()
        return WarehouseSnapshot(
            self.id, self.is_active, self.default_storage_location_id
        )

    def set_default_storage_location(self, location: StockLocationSnapshot) -> Self:
        """Назначает активную STORAGE того же склада, сохраняя остальные собственные значения."""
        DefaultStorageLocationPolicy.ensure_assignable(
            location=location, warehouse=self.snapshot()
        )
        return self._with_changes(default_storage_location_id=location.id)

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
            or (
                self.default_storage_location_id is not None
                and not isinstance(self.default_storage_location_id, StockLocationIdVO)
            )
        ):
            raise InvalidWarehouseValueError(
                "Нужны типизированные ID, код, название и bool активности склада."
            )
