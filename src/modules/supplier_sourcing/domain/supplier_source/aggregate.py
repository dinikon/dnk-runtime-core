from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from dataclasses import dataclass, replace
from typing import Self

from src.modules.supplier_sourcing.domain.supplier_source.availability_snapshot import (
    SupplierSourceAvailabilitySnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
    SupplierSourceInactiveError,
    UnsupportedSupplierFulfillmentModeError,
)
from src.modules.supplier_sourcing.domain.supplier_source.identity_snapshot import (
    SupplierSourceIdentitySnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.external_warehouse_code import (
    ExternalWarehouseCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import (
    SupplierSourceNameVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    SupplierStockUpdatePolicyVO,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import (
    SupplierLeadTimeVO,
)


@dataclass(frozen=True, slots=True)
class SupplierSource:
    """Описывает отдельный источник поставщика и правила его использования."""

    id: SupplierSourceIdVO
    supplier: SupplierReferenceVO
    name: SupplierSourceNameVO
    external_warehouse_code: ExternalWarehouseCodeVO | None
    fulfillment_modes: frozenset[SupplierFulfillmentMode]
    is_active: bool
    stock_update_policy: SupplierStockUpdatePolicyVO
    default_lead_time: SupplierLeadTimeVO

    @classmethod
    def create(
        cls,
        *,
        identifier: SupplierSourceIdVO,
        supplier: SupplierReferenceVO,
        name: SupplierSourceNameVO,
        fulfillment_modes: frozenset[SupplierFulfillmentMode],
        stock_update_policy: SupplierStockUpdatePolicyVO,
        default_lead_time: SupplierLeadTimeVO,
        external_warehouse_code: ExternalWarehouseCodeVO | None = None,
    ) -> Self:
        """Создаёт активный источник с явно переданной идентичностью и настройками."""
        return cls.restore(
            identifier=identifier,
            supplier=supplier,
            name=name,
            external_warehouse_code=external_warehouse_code,
            fulfillment_modes=fulfillment_modes,
            is_active=True,
            stock_update_policy=stock_update_policy,
            default_lead_time=default_lead_time,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: SupplierSourceIdVO,
        supplier: SupplierReferenceVO,
        name: SupplierSourceNameVO,
        external_warehouse_code: ExternalWarehouseCodeVO | None,
        fulfillment_modes: frozenset[SupplierFulfillmentMode],
        is_active: bool,
        stock_update_policy: SupplierStockUpdatePolicyVO,
        default_lead_time: SupplierLeadTimeVO,
    ) -> Self:
        """Восстанавливает полную карточку с прежней принадлежностью и активностью."""
        source = cls(
            id=identifier,
            supplier=supplier,
            name=name,
            external_warehouse_code=external_warehouse_code,
            fulfillment_modes=fulfillment_modes,
            is_active=is_active,
            stock_update_policy=stock_update_policy,
            default_lead_time=default_lead_time,
        )
        source._validate()
        return source

    def rename(self, name: SupplierSourceNameVO) -> Self:
        """Возвращает источник с новым отображаемым названием."""
        return self._with_changes(name=name)

    def identity_snapshot(self) -> SupplierSourceIdentitySnapshot:
        """Возвращает идентификатор источника и ссылку на его поставщика."""
        self._validate()
        return SupplierSourceIdentitySnapshot(self.id, self.supplier)

    def availability_snapshot(self) -> SupplierSourceAvailabilitySnapshot:
        """Возвращает идентичность и правила обработки наблюдений наличия."""
        return SupplierSourceAvailabilitySnapshot(
            self.identity_snapshot(), self.stock_update_policy
        )

    def change_external_warehouse_code(
        self, code: ExternalWarehouseCodeVO | None
    ) -> Self:
        """Назначает новый код в системе поставщика или убирает прежнюю ссылку."""
        return self._with_changes(external_warehouse_code=code)

    def configure_fulfillment(
        self,
        *,
        fulfillment_modes: frozenset[SupplierFulfillmentMode],
        default_lead_time: SupplierLeadTimeVO,
    ) -> Self:
        """Задаёт разрешённые маршруты поставки и общий срок источника."""
        return self._with_changes(
            fulfillment_modes=fulfillment_modes, default_lead_time=default_lead_time
        )

    def change_stock_update_policy(self, policy: SupplierStockUpdatePolicyVO) -> Self:
        """Заменяет настройки актуальности внешних наблюдений."""
        return self._with_changes(stock_update_policy=policy)

    def activate(self) -> Self:
        """Разрешает выбор источника по поддерживаемым маршрутам."""
        return self._with_changes(is_active=True)

    def deactivate(self) -> Self:
        """Блокирует выбор источника до повторной активации."""
        return self._with_changes(is_active=False)

    def ensure_supports(self, mode: SupplierFulfillmentMode) -> None:
        """Требует активный источник с разрешённым режимом поставки."""
        self._validate()
        if not isinstance(mode, SupplierFulfillmentMode):
            raise InvalidSupplierSourceValueError(
                "Нужен типизированный режим поставки."
            )
        if not self.is_active:
            raise SupplierSourceInactiveError("Источник поставщика деактивирован.")
        if mode not in self.fulfillment_modes:
            raise UnsupportedSupplierFulfillmentModeError(
                "Источник не поддерживает выбранный режим поставки."
            )

    def _with_changes(self, **changes: object) -> Self:
        """Проверяет новую карточку и сохраняет исходный экземпляр."""
        source = replace(self, **changes)
        source._validate()
        return source

    def _validate(self) -> None:
        """Требует номинальные поля, явную активность и непустой набор режимов."""
        if (
            not isinstance(self.id, SupplierSourceIdVO)
            or not isinstance(self.supplier, SupplierReferenceVO)
            or not isinstance(self.name, SupplierSourceNameVO)
            or (
                self.external_warehouse_code is not None
                and not isinstance(
                    self.external_warehouse_code, ExternalWarehouseCodeVO
                )
            )
            or type(self.is_active) is not bool
            or not isinstance(self.stock_update_policy, SupplierStockUpdatePolicyVO)
            or not isinstance(self.default_lead_time, SupplierLeadTimeVO)
        ):
            raise InvalidSupplierSourceValueError(
                "Нужны типизированные идентификаторы, название, настройки и признак активности источника."
            )
        if (
            not isinstance(self.fulfillment_modes, frozenset)
            or not self.fulfillment_modes
            or any(
                not isinstance(mode, SupplierFulfillmentMode)
                for mode in self.fulfillment_modes
            )
        ):
            raise InvalidSupplierSourceValueError(
                "Источник должен поддерживать хотя бы один типизированный режим поставки."
            )
