from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

from src.modules.external_fulfillment.domain.assignment_snapshot import (
    SupplierFulfillmentAssignmentSnapshot,
    SupplierFulfillmentDraftSnapshot,
)
from src.modules.external_fulfillment.domain.confirmation_snapshot import (
    SupplierFulfillmentConfirmationSnapshot,
)
from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentAllocationSnapshot,
    SupplierFulfillmentOfferSnapshot,
    SupplierFulfillmentPlanBasisSnapshot,
    SupplierFulfillmentSourceSnapshot,
)
from src.modules.external_fulfillment.domain.draft_policy import (
    SupplierFulfillmentDraftPolicy,
)
from src.modules.external_fulfillment.domain.entity.supplier_fulfillment_line import (
    SupplierFulfillmentLine,
)
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
    SupplierFulfillmentBasisMismatchError,
    SupplierFulfillmentStatusError,
    SupplierFulfillmentTimeError,
    SupplierFulfillmentVersionConflictError,
)
from src.modules.external_fulfillment.domain.rejection_snapshot import (
    SupplierFulfillmentRejectionSnapshot,
)
from src.modules.external_fulfillment.domain.shipment_snapshot import (
    SupplierFulfillmentShipmentSnapshot,
)
from src.modules.external_fulfillment.domain.time import (
    normalize_supplier_fulfillment_time,
)
from src.modules.external_fulfillment.domain.value_object.delivery_address import (
    SupplierDeliveryAddressVO,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentOrderIdVO,
)
from src.modules.external_fulfillment.domain.value_object.line_binding import (
    SupplierFulfillmentLineBindingVO,
)
from src.modules.external_fulfillment.domain.value_object.line_confirmation import (
    SupplierFulfillmentLineConfirmationVO,
)
from src.modules.external_fulfillment.domain.value_object.plan_ref import (
    SupplierFulfillmentPlanRefVO,
)
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalSupplierSourceIdVO,
)
from src.modules.external_fulfillment.domain.value_object.shipment import (
    SupplierFulfillmentShipmentLineVO,
    SupplierFulfillmentShipmentVO,
)
from src.modules.external_fulfillment.domain.value_object.status import (
    SupplierFulfillmentOrderStatus,
)

_CONFIRMATION_VERSION = 2
_SHIPMENT_VERSION = 3


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentOrder:
    """Хранит заявку на прямую поставку от одного поставщика и источника."""

    id: SupplierFulfillmentOrderIdVO
    supplier: ExternalSupplierReferenceVO
    supplier_source_id: ExternalSupplierSourceIdVO
    plan_ref: SupplierFulfillmentPlanRefVO
    delivery_address: SupplierDeliveryAddressVO
    lines: tuple[SupplierFulfillmentLine, ...]
    status: SupplierFulfillmentOrderStatus
    created_at: datetime
    version: int
    requested_at: datetime | None = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    shipment: SupplierFulfillmentShipmentVO | None = None

    @classmethod
    def create_from_plan(
        cls,
        *,
        identifier: SupplierFulfillmentOrderIdVO,
        basis: SupplierFulfillmentPlanBasisSnapshot,
        source: SupplierFulfillmentSourceSnapshot,
        offers: tuple[SupplierFulfillmentOfferSnapshot, ...],
        line_bindings: tuple[SupplierFulfillmentLineBindingVO, ...],
        delivery_address: SupplierDeliveryAddressVO,
        created_at: datetime,
    ) -> Self:
        """Создаёт DRAFT с количеством и ценой исходных распределений, версией ноль."""
        lines = SupplierFulfillmentDraftPolicy.build_lines(
            basis=basis, source=source, offers=offers, line_bindings=line_bindings
        )
        at = normalize_supplier_fulfillment_time(created_at)
        if at < basis.plan_updated_at:
            raise SupplierFulfillmentTimeError(
                "Черновик не может предшествовать выбранной версии плана."
            )
        return cls.restore(
            identifier=identifier,
            supplier=source.supplier,
            supplier_source_id=source.id,
            plan_ref=basis.plan_ref,
            delivery_address=delivery_address,
            lines=lines,
            status=SupplierFulfillmentOrderStatus.DRAFT,
            created_at=at,
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: SupplierFulfillmentOrderIdVO,
        supplier: ExternalSupplierReferenceVO,
        supplier_source_id: ExternalSupplierSourceIdVO,
        plan_ref: SupplierFulfillmentPlanRefVO,
        delivery_address: SupplierDeliveryAddressVO,
        lines: tuple[SupplierFulfillmentLine, ...],
        status: SupplierFulfillmentOrderStatus,
        created_at: datetime,
        version: int,
        requested_at: datetime | None = None,
        confirmed_at: datetime | None = None,
        rejected_at: datetime | None = None,
        rejection_reason: str | None = None,
        shipment: SupplierFulfillmentShipmentVO | None = None,
    ) -> Self:
        """Восстанавливает заказ и сохранённый ответ поставщика."""
        order = cls(
            identifier,
            supplier,
            supplier_source_id,
            plan_ref,
            delivery_address,
            lines,
            status,
            normalize_supplier_fulfillment_time(created_at),
            version,
            (
                normalize_supplier_fulfillment_time(requested_at)
                if requested_at is not None
                else None
            ),
            (
                normalize_supplier_fulfillment_time(confirmed_at)
                if confirmed_at is not None
                else None
            ),
            (
                normalize_supplier_fulfillment_time(rejected_at)
                if rejected_at is not None
                else None
            ),
            rejection_reason,
            shipment,
        )
        order._validate()
        return order

    def draft_snapshot(self) -> SupplierFulfillmentDraftSnapshot:
        """Экспортирует черновик для повторной сверки и закрепления всех его строк."""
        self._validate()
        if self.status is not SupplierFulfillmentOrderStatus.DRAFT:
            raise SupplierFulfillmentStatusError(
                "Для закрепления нужен черновик внешнего заказа."
            )
        return SupplierFulfillmentDraftSnapshot(
            self.id,
            self.version,
            self.supplier,
            self.plan_ref,
            self.created_at,
            self._allocation_snapshots(),
            self._line_bindings(),
        )

    def request(
        self,
        assignment: SupplierFulfillmentAssignmentSnapshot,
        *,
        expected_version: int,
        requested_at: datetime,
    ) -> Self:
        """Фиксирует готовность запроса по полному актуальному закреплению в плане."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidSupplierFulfillmentValueError(
                "Ожидаемая версия должна быть целым числом от нуля."
            )
        if expected_version != self.version:
            raise SupplierFulfillmentVersionConflictError(
                "Версия внешнего заказа устарела."
            )
        if self.status is not SupplierFulfillmentOrderStatus.DRAFT:
            raise SupplierFulfillmentStatusError(
                "Запрос можно подготовить только из черновика."
            )
        if not isinstance(assignment, SupplierFulfillmentAssignmentSnapshot):
            raise InvalidSupplierFulfillmentValueError(
                "Нужен специализированный снимок закрепления."
            )
        assignment.ensure_valid()
        if (
            assignment.order_id != self.id
            or assignment.order_version != self.version
            or assignment.supplier != self.supplier
            or assignment.basis.plan_ref.plan_id != self.plan_ref.plan_id
            or assignment.source_plan_version != self.plan_ref.plan_version
            or set(assignment.basis.allocations) != set(self._allocation_snapshots())
            or len(assignment.line_bindings) != len(self.lines)
            or set(assignment.line_bindings) != set(self._line_bindings())
        ):
            raise SupplierFulfillmentBasisMismatchError(
                "Запрос требует закрепления всех прежних строк за этим заказом и версией черновика."
            )
        at = normalize_supplier_fulfillment_time(requested_at)
        if (
            assignment.assigned_at < self.created_at
            or at < assignment.basis.plan_updated_at
        ):
            raise SupplierFulfillmentTimeError(
                "Запрос должен следовать за созданием черновика и текущим закреплением."
            )
        terms = dict(assignment.quantity_terms)
        requested = replace(
            self,
            lines=tuple(
                replace(line, quantity_terms=terms.get(line.id)) for line in self.lines
            ),
            status=SupplierFulfillmentOrderStatus.REQUESTED,
            requested_at=at,
            version=self.version + 1,
        )
        requested._validate()
        return requested

    def confirm(
        self,
        lines: tuple[SupplierFulfillmentLineConfirmationVO, ...],
        *,
        expected_version: int,
        confirmed_at: datetime,
    ) -> Self:
        """Регистрирует полный или частичный ответ по всем строкам запроса."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidSupplierFulfillmentValueError(
                "Ожидаемая версия должна быть целым числом от нуля."
            )
        if expected_version != self.version:
            raise SupplierFulfillmentVersionConflictError(
                "Версия внешнего заказа устарела."
            )
        if (
            self.requested_at is None
            or self.status is SupplierFulfillmentOrderStatus.REJECTED
        ):
            raise SupplierFulfillmentStatusError(
                "Подтверждение требует запрос без отказа поставщика."
            )
        at = normalize_supplier_fulfillment_time(confirmed_at)
        if at < self.requested_at:
            raise SupplierFulfillmentTimeError(
                "Подтверждение не может предшествовать запросу."
            )
        if not isinstance(lines, tuple) or any(
            not isinstance(line, SupplierFulfillmentLineConfirmationVO)
            for line in lines
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужен tuple подтверждений строк."
            )
        by_id = {line.line_id: line for line in lines}
        if len(by_id) != len(lines) or set(by_id) != {line.id for line in self.lines}:
            raise SupplierFulfillmentBasisMismatchError(
                "Подтверждение должно включать все строки запроса ровно один раз."
            )
        confirmed_lines = tuple(line.confirm(by_id[line.id]) for line in self.lines)
        status = self._confirmation_status(confirmed_lines)
        if status is None:
            raise SupplierFulfillmentBasisMismatchError(
                "Подтверждение требует положительное количество хотя бы по одной строке."
            )
        if self.confirmed_at is not None:
            if at == self.confirmed_at and confirmed_lines == self.lines:
                return self
            raise SupplierFulfillmentBasisMismatchError(
                "Состав и момент зарегистрированного ответа нельзя изменить."
            )
        confirmed = replace(
            self,
            lines=confirmed_lines,
            status=status,
            confirmed_at=at,
            version=self.version + 1,
        )
        confirmed._validate()
        return confirmed

    def reject(
        self,
        *,
        expected_version: int,
        rejected_at: datetime,
        reason: str | None = None,
    ) -> Self:
        """Фиксирует явный отказ по всему подготовленному запросу."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidSupplierFulfillmentValueError(
                "Ожидаемая версия должна быть целым числом от нуля."
            )
        if expected_version != self.version:
            raise SupplierFulfillmentVersionConflictError(
                "Версия внешнего заказа устарела."
            )
        if self.status not in (
            SupplierFulfillmentOrderStatus.REQUESTED,
            SupplierFulfillmentOrderStatus.REJECTED,
        ):
            raise SupplierFulfillmentStatusError(
                "Отказ допустим по запросу без подтверждённого обязательства."
            )
        at = normalize_supplier_fulfillment_time(rejected_at)
        if self.requested_at is None or at < self.requested_at:
            raise SupplierFulfillmentTimeError("Отказ не может предшествовать запросу.")
        if self.status is SupplierFulfillmentOrderStatus.REJECTED:
            if at == self.rejected_at and reason == self.rejection_reason:
                return self
            raise SupplierFulfillmentBasisMismatchError(
                "Момент и причину зарегистрированного отказа нельзя изменить."
            )
        rejected = replace(
            self,
            status=SupplierFulfillmentOrderStatus.REJECTED,
            rejected_at=at,
            rejection_reason=reason,
            version=self.version + 1,
        )
        rejected._validate()
        return rejected

    def rejection_snapshot(self) -> SupplierFulfillmentRejectionSnapshot:
        """Передаёт полный состав отклонённого запроса для регистрации в плане."""
        self._validate()
        if self.requested_at is None or self.rejected_at is None:
            raise SupplierFulfillmentStatusError(
                "Для экспорта требуется отклонённый поставщиком заказ."
            )
        return SupplierFulfillmentRejectionSnapshot(
            self.id,
            self.version,
            self.supplier,
            self.plan_ref,
            self.requested_at,
            self.rejected_at,
            self._allocation_snapshots(),
            self._line_bindings(),
        )

    def register_shipment(
        self,
        shipment: SupplierFulfillmentShipmentVO,
        lines: tuple[SupplierFulfillmentShipmentLineVO, ...],
        *,
        expected_version: int,
    ) -> Self:
        """Фиксирует отправку всего подтверждённого количества одним фактом."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidSupplierFulfillmentValueError(
                "Ожидаемая версия должна быть целым числом от нуля."
            )
        if expected_version != self.version:
            raise SupplierFulfillmentVersionConflictError(
                "Версия внешнего заказа устарела."
            )
        if self.confirmed_at is None:
            raise SupplierFulfillmentStatusError(
                "Внешняя отправка требует подтверждённый заказ."
            )
        if (
            not isinstance(shipment, SupplierFulfillmentShipmentVO)
            or not isinstance(lines, tuple)
            or any(
                not isinstance(line, SupplierFulfillmentShipmentLineVO)
                for line in lines
            )
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужен факт отправки с типизированными строками."
            )
        if shipment.shipped_at < self.confirmed_at:
            raise SupplierFulfillmentTimeError(
                "Отправка не может предшествовать подтверждению."
            )
        by_id = {line.line_id: line.quantity for line in lines}
        confirmed_ids = {
            line.id
            for line in self.lines
            if line.confirmed_quantity is not None
            and not line.confirmed_quantity.value.is_zero()
        }
        if len(by_id) != len(lines) or by_id.keys() != confirmed_ids:
            raise SupplierFulfillmentBasisMismatchError(
                "Отправка должна включать все положительно подтверждённые строки ровно один раз."
            )
        shipped_lines = tuple(
            line.ship(by_id[line.id]) if line.id in by_id else line
            for line in self.lines
        )
        if self.shipment is not None:
            if self.shipment == shipment and self.lines == shipped_lines:
                return self
            raise SupplierFulfillmentBasisMismatchError(
                "Зарегистрированную внешнюю отправку нельзя изменить."
            )
        shipped = replace(
            self,
            lines=shipped_lines,
            status=SupplierFulfillmentOrderStatus.SHIPPED,
            shipment=shipment,
            version=self.version + 1,
        )
        shipped._validate()
        return shipped

    def shipment_snapshot(self) -> SupplierFulfillmentShipmentSnapshot:
        """Передаёт отправку и историческое подтверждение для регистрации в плане."""
        self._validate()
        if self.shipment is None:
            raise SupplierFulfillmentStatusError(
                "Для экспорта требуется зарегистрированная отправка."
            )
        return SupplierFulfillmentShipmentSnapshot(
            self.confirmation_snapshot(),
            self.shipment,
            self.version,
            tuple(
                SupplierFulfillmentShipmentLineVO(line.id, line.shipped_quantity)
                for line in self.lines
                if not line.shipped_quantity.value.is_zero()
            ),
        )

    def confirmation_snapshot(self) -> SupplierFulfillmentConfirmationSnapshot:
        """Передаёт исходный запрос и фактический ответ для регистрации в плане."""
        self._validate()
        if self.requested_at is None or self.confirmed_at is None:
            raise SupplierFulfillmentStatusError(
                "Для экспорта требуется подтверждённый заказ."
            )
        return SupplierFulfillmentConfirmationSnapshot(
            self.id,
            _CONFIRMATION_VERSION,
            self.supplier,
            self.plan_ref,
            self.requested_at,
            self.confirmed_at,
            self._allocation_snapshots(),
            self._line_bindings(),
            tuple(
                SupplierFulfillmentLineConfirmationVO(
                    line.id, line.confirmed_quantity, line.confirmed_price
                )
                for line in self.lines
                if line.confirmed_quantity is not None
            ),
        )

    @staticmethod
    def _confirmation_status(
        lines: tuple[SupplierFulfillmentLine, ...],
    ) -> SupplierFulfillmentOrderStatus | None:
        """Определяет состояние окончательного ответа по положительным количествам."""
        if not any(
            line.confirmed_quantity is not None
            and not line.confirmed_quantity.value.is_zero()
            for line in lines
        ):
            return None
        if all(line.confirmed_quantity == line.requested_quantity for line in lines):
            return SupplierFulfillmentOrderStatus.CONFIRMED
        return SupplierFulfillmentOrderStatus.PARTIALLY_CONFIRMED

    def _allocation_snapshots(
        self,
    ) -> tuple[SupplierFulfillmentAllocationSnapshot, ...]:
        """Возвращает закрепляемые исходные количество, цену и коммерческие ссылки строк."""
        return tuple(
            SupplierFulfillmentAllocationSnapshot(
                line.fulfillment_allocation_id,
                line.inventory_item_id,
                self.supplier_source_id,
                line.supplier_offer_id,
                line.base_uom,
                line.requested_quantity,
                line.quoted_price,
            )
            for line in self.lines
        )

    def _line_bindings(self) -> tuple[SupplierFulfillmentLineBindingVO, ...]:
        """Возвращает точное соответствие распределений строкам внешнего заказа."""
        return tuple(
            SupplierFulfillmentLineBindingVO(line.fulfillment_allocation_id, line.id)
            for line in self.lines
        )

    def _validate(self) -> None:
        """Проверяет матрицу статуса и дат, уникальность строк и распределений."""
        if (
            not isinstance(self.id, SupplierFulfillmentOrderIdVO)
            or not isinstance(self.supplier, ExternalSupplierReferenceVO)
            or not isinstance(self.supplier_source_id, ExternalSupplierSourceIdVO)
            or not isinstance(self.plan_ref, SupplierFulfillmentPlanRefVO)
            or not isinstance(self.delivery_address, SupplierDeliveryAddressVO)
            or not isinstance(self.status, SupplierFulfillmentOrderStatus)
            or type(self.version) is not int
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужен типизированный внешний заказ с адресом и непустыми строками."
            )
        if self.status is SupplierFulfillmentOrderStatus.DRAFT:
            valid_state = (
                self.version == 0
                and self.requested_at is None
                and self.confirmed_at is None
            )
        elif self.status is SupplierFulfillmentOrderStatus.REQUESTED:
            valid_state = (
                self.version == 1
                and self.requested_at is not None
                and self.confirmed_at is None
            )
        elif self.status is SupplierFulfillmentOrderStatus.REJECTED:
            valid_state = (
                self.version == 2
                and self.requested_at is not None
                and self.confirmed_at is None
                and self.rejected_at is not None
            )
        elif self.status is SupplierFulfillmentOrderStatus.SHIPPED:
            valid_state = (
                self.version == _SHIPMENT_VERSION
                and self.requested_at is not None
                and self.confirmed_at is not None
                and isinstance(self.shipment, SupplierFulfillmentShipmentVO)
            )
        else:
            valid_state = (
                self.version == _CONFIRMATION_VERSION
                and self.requested_at is not None
                and self.confirmed_at is not None
            )
        if (
            self.status is not SupplierFulfillmentOrderStatus.SHIPPED
            and self.shipment is not None
        ):
            valid_state = False
        if self.status is not SupplierFulfillmentOrderStatus.REJECTED and (
            self.rejected_at is not None or self.rejection_reason is not None
        ):
            valid_state = False
        if not valid_state:
            raise InvalidSupplierFulfillmentValueError(
                "Статус, версия и время запроса или ответа не согласованы."
            )
        if self.rejection_reason is not None and (
            not isinstance(self.rejection_reason, str)
            or not self.rejection_reason.strip()
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Переданная причина отказа должна быть непустым текстом."
            )
        normalize_supplier_fulfillment_time(self.created_at)
        if self.created_at.utcoffset() != timedelta(0):
            raise SupplierFulfillmentTimeError("Время создания должно храниться в UTC.")
        if self.requested_at is not None:
            normalize_supplier_fulfillment_time(self.requested_at)
            if (
                self.requested_at.utcoffset() != timedelta(0)
                or self.requested_at < self.created_at
            ):
                raise SupplierFulfillmentTimeError(
                    "Время запроса должно храниться в UTC после создания."
                )
        if self.confirmed_at is not None:
            normalize_supplier_fulfillment_time(self.confirmed_at)
            if (
                self.confirmed_at.utcoffset() != timedelta(0)
                or self.requested_at is None
                or self.confirmed_at < self.requested_at
            ):
                raise SupplierFulfillmentTimeError(
                    "Время подтверждения должно храниться в UTC после запроса."
                )
        if self.rejected_at is not None:
            normalize_supplier_fulfillment_time(self.rejected_at)
            if (
                self.rejected_at.utcoffset() != timedelta(0)
                or self.requested_at is None
                or self.rejected_at < self.requested_at
            ):
                raise SupplierFulfillmentTimeError(
                    "Время отказа должно храниться в UTC после запроса."
                )
        if self.shipment is not None and (
            self.confirmed_at is None or self.shipment.shipped_at < self.confirmed_at
        ):
            raise SupplierFulfillmentTimeError(
                "Время отправки должно следовать за подтверждением."
            )
        line_ids = set()
        allocation_ids = set()
        for line in self.lines:
            if not isinstance(line, SupplierFulfillmentLine):
                raise InvalidSupplierFulfillmentValueError(
                    "Нужны строки внешнего заказа."
                )
            line.ensure_valid()
            if self.requested_at is None and line.quantity_terms is not None:
                raise InvalidSupplierFulfillmentValueError(
                    "Правила количества сохраняются при подготовке запроса."
                )
            if (line.confirmed_quantity is not None) != (self.confirmed_at is not None):
                raise InvalidSupplierFulfillmentValueError(
                    "Состояние каждой строки должно соответствовать подтверждению заказа."
                )
            if self.shipment is None:
                valid_shipment = line.shipped_quantity.value.is_zero()
            else:
                valid_shipment = line.shipped_quantity == line.confirmed_quantity
            if not valid_shipment:
                raise InvalidSupplierFulfillmentValueError(
                    "Отправка должна охватывать всё подтверждённое количество заказа."
                )
            if line.id in line_ids or line.fulfillment_allocation_id in allocation_ids:
                raise InvalidSupplierFulfillmentValueError(
                    "ID строки и распределение должны быть уникальны в заказе."
                )
            line_ids.add(line.id)
            allocation_ids.add(line.fulfillment_allocation_id)
        if self.confirmed_at is not None:
            confirmation_status = self._confirmation_status(self.lines)
            if confirmation_status is None or (
                self.shipment is None and self.status is not confirmation_status
            ):
                raise InvalidSupplierFulfillmentValueError(
                    "Статус заказа должен соответствовать подтверждённым количествам."
                )
        if any(line.quantity_terms is not None for line in self.lines) and any(
            line.quantity_terms is None for line in self.lines
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Правила запроса сохраняются по всему составу."
            )
