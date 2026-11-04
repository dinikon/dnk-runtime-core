from datetime import datetime, timedelta
from typing import ClassVar
from uuid import UUID

from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.policy.stock_document_confirmation import (
    StockDocumentConfirmationPolicy,
)
from src.modules.inventory.domain.shipment.document_snapshot import (
    ShipmentDocumentSnapshot,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentDocumentSnapshotError,
    ShipmentStatusError,
)
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidShipmentDocumentLineBindingError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentLineError,
    StaleShipmentDocumentSourceError,
    StockDocumentShipmentMismatchError,
    StockDocumentShipmentQuantityExceededError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.shipment_line_binding import (
    ShipmentDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentDocumentPolicy:
    """Строит расходный план по остаткам отправления и повторно проверяет его основание перед подтверждением."""

    SOURCE_SYSTEM: ClassVar[str] = "inventory.shipment"
    LINE_SOURCE_SYSTEM: ClassVar[str] = "inventory.shipment_line"

    @staticmethod
    def build_lines(
        *,
        shipment: ShipmentDocumentSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        line_bindings: tuple[ShipmentDocumentLineBindingVO, ...],
        as_of: datetime,
    ) -> tuple[StockDocumentLine, ...]:
        """Выводит одну строку на каждый открытый остаток без генерации ID и повторного пересчёта основания."""
        ShipmentDocumentPolicy._ensure_shipment(shipment, as_of)
        StockDocumentConfirmationPolicy.ensure_warehouse(
            warehouse_id=shipment.warehouse_id, warehouse=warehouse
        )
        if not isinstance(inventory_items, tuple):
            raise InvalidStockDocumentContextError(
                "Нужен tuple текущих снимков товаров расходного документа."
            )
        by_item = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemDocumentSnapshot):
                raise InvalidInventoryItemDocumentSnapshotError(
                    "Нужны снимки товаров для документа."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InvalidStockDocumentContextError(
                    "Снимок каждого товара передаётся один раз."
                )
            by_item[item.inventory_item_id] = item
        if set(by_item) != {line.inventory_item_id for line in shipment.lines}:
            raise InvalidStockDocumentContextError(
                "Нужны ровно участвующие снимки товаров без пропусков и лишних."
            )
        if not isinstance(line_bindings, tuple):
            raise InvalidShipmentDocumentLineBindingError(
                "Нужен tuple соответствий новых ID строк документа."
            )
        by_line, document_ids = {}, set()
        for binding in line_bindings:
            if not isinstance(binding, ShipmentDocumentLineBindingVO):
                raise InvalidShipmentDocumentLineBindingError(
                    "Нужны ShipmentDocumentLineBindingVO."
                )
            if (
                binding.shipment_line_id in by_line
                or binding.document_line_id in document_ids
            ):
                raise InvalidShipmentDocumentLineBindingError(
                    "Строка основания и новый ID строки назначаются только один раз."
                )
            by_line[binding.shipment_line_id] = binding.document_line_id
            document_ids.add(binding.document_line_id)
        if set(by_line) != {line.shipment_line_id for line in shipment.lines}:
            raise InvalidShipmentDocumentLineBindingError(
                "Нужны ровно все оставшиеся строки отправления."
            )
        lines = []
        for line in sorted(
            shipment.lines, key=lambda value: value.shipment_line_id.uuid.int
        ):
            item = by_item[line.inventory_item_id]
            if item.base_uom != line.base_uom:
                raise StockDocumentUomMismatchError(
                    "Базовая единица товара не соответствует остатку отправления."
                )
            lines.append(
                StockDocumentLine.create(
                    identifier=by_line[line.shipment_line_id],
                    inventory_item=item,
                    quantity=line.remaining_qty,
                    uom=line.base_uom,
                    source=DocumentLineSourceVO(
                        ShipmentDocumentPolicy.LINE_SOURCE_SYSTEM,
                        str(line.shipment_line_id.uuid),
                    ),
                )
            )
        return tuple(lines)

    @staticmethod
    def ensure_document_source(
        *,
        operation_type: StockOperationType,
        source: DocumentSourceVO | None,
        lines: tuple[StockDocumentLine, ...],
    ) -> None:
        """Проверяет собственную структуру зарезервированных оснований документа без актуального отправления."""
        if (
            source is not None and not isinstance(source, DocumentSourceVO)
        ) or not isinstance(lines, tuple):
            raise StockDocumentShipmentMismatchError(
                "Некорректные основание или состав документа."
            )
        linked = (
            source is not None and source.system == ShipmentDocumentPolicy.SOURCE_SYSTEM
        )
        refs = set()
        for line in lines:
            if not isinstance(line, StockDocumentLine):
                raise InvalidStockDocumentLineError(
                    "Нужны строки складского документа."
                )
            line.ensure_valid()
            if linked:
                if (
                    line.source is None
                    or line.source.system != ShipmentDocumentPolicy.LINE_SOURCE_SYSTEM
                ):
                    raise StockDocumentShipmentMismatchError(
                        "Каждая строка расходного документа должна ссылаться на строку Shipment."
                    )
                ShipmentDocumentPolicy._ensure_canonical_reference(
                    line.source.reference
                )
                if line.source.reference in refs:
                    raise StockDocumentShipmentMismatchError(
                        "Строка Shipment не должна повторяться в документе."
                    )
                refs.add(line.source.reference)
            elif (
                line.source is not None
                and line.source.system == ShipmentDocumentPolicy.LINE_SOURCE_SYSTEM
            ):
                raise StockDocumentShipmentMismatchError(
                    "Основание ShipmentLine требует основания Shipment в шапке документа."
                )
        if linked:
            if operation_type is not StockOperationType.ISSUE or source.version is None:
                raise StockDocumentShipmentMismatchError(
                    "Основание Shipment требует ISSUE и явно сохранённую версию."
                )
            ShipmentDocumentPolicy._ensure_canonical_reference(source.reference)

    @staticmethod
    def ensure_confirmable(
        *,
        operation_type: StockOperationType,
        source: DocumentSourceVO | None,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        lines: tuple[StockDocumentLine, ...],
        shipment: ShipmentDocumentSnapshot | None,
        as_of: datetime,
    ) -> None:
        """Требует свежую версию того же основания и допустимые остатки каждой сохранённой привязки."""
        ShipmentDocumentPolicy.ensure_document_source(
            operation_type=operation_type, source=source, lines=lines
        )
        if source is None or source.system != ShipmentDocumentPolicy.SOURCE_SYSTEM:
            if shipment is not None:
                raise InvalidStockDocumentContextError(
                    "Снимок Shipment передаётся только для документа с соответствующим основанием."
                )
            return
        ShipmentDocumentPolicy._ensure_shipment(shipment, as_of)
        if (
            source.reference != str(shipment.id.uuid)
            or warehouse_id != shipment.warehouse_id
            or owner_id != shipment.owner_id
        ):
            raise StockDocumentShipmentMismatchError(
                "Отправление, склад и владелец не соответствуют основанию документа."
            )
        if source.version != shipment.version:
            raise StaleShipmentDocumentSourceError(
                "Версия основания изменилась; требуется построить документ заново."
            )
        by_line = {str(line.shipment_line_id.uuid): line for line in shipment.lines}
        for line in lines:
            target = by_line.get(line.source.reference)
            if (
                target is None
                or target.inventory_item_id != line.inventory_item_id
                or target.base_uom != line.base_uom
            ):
                raise StockDocumentShipmentMismatchError(
                    "Строка, товар или единица не соответствуют открытому остатку Shipment."
                )
            if line.planned_qty.value > target.remaining_qty.value:
                raise StockDocumentShipmentQuantityExceededError(
                    "План строки документа превышает остаток отправления."
                )

    @staticmethod
    def _ensure_shipment(shipment: ShipmentDocumentSnapshot, as_of: datetime) -> None:
        """Проверяет специализированный снимок, состояние с остатком и явное время решения в UTC."""
        if not isinstance(shipment, ShipmentDocumentSnapshot):
            raise InvalidShipmentDocumentSnapshotError(
                "Нужен текущий снимок остатков Shipment для документа."
            )
        shipment.ensure_valid()
        if shipment.status not in (
            ShipmentStatus.CONFIRMED,
            ShipmentStatus.PARTIALLY_SHIPPED,
        ):
            raise ShipmentStatusError(
                "Расходный документ доступен только для подтверждённого или частично отгруженного Shipment."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < shipment.updated_at
        ):
            raise StockDocumentTimeError(
                "Время решения должно быть в UTC и не раньше состояния отправления."
            )

    @staticmethod
    def _ensure_canonical_reference(reference: str) -> None:
        """Требует канонический UUID ссылки, не нормализуя сохранённую историю автоматически."""
        try:
            if str(UUID(reference)) != reference:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise StockDocumentShipmentMismatchError(
                "Основание Shipment и его строк должно содержать канонический UUID."
            ) from exc
