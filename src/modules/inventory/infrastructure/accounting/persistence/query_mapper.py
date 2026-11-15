from src.modules.inventory.infrastructure.persistence.models.stock_execution_return import (
    StockExecutionReturnModel as ReturnDetails,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_status_change import (
    StockExecutionStatusChangeModel as StatusDetails,
)
from src.modules.inventory.application.stock_position.query.list_stock_balances.dto import (
    ListStockBalancesItemDTO,
)
from decimal import Decimal
from uuid import UUID
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as P,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel as L,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as W,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel as I,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel as Lot,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel as S,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as E,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel as T,
)
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import (
    StockLedgerEntryModel as Entry,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel as D,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.dto import (
    ListStockPositionsItemDTO,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.dto import (
    GetStockPositionResultDTO,
)
from src.modules.inventory.application.stock_posting.query.list_stock_movements.dto import (
    ListStockMovementsItemDTO,
)


class StockAccountingQueryMapper:
    """Преобразует только типизированные SQL-проекции без доменных фабрик и запросов."""

    @staticmethod
    def position(
        p: P, l: L, w: W, item: I, lot: Lot | None, serial: S | None
    ) -> ListStockPositionsItemDTO:
        """Создаёт собственный DTO сценария с точными количествами."""
        return ListStockPositionsItemDTO(
            id=p.id,
            inventory_item_id=p.inventory_item_id,
            sku=item.sku,
            warehouse_id=w.id,
            warehouse_code=w.code,
            warehouse_name=w.name,
            warehouse_is_active=w.is_active,
            location_id=l.id,
            location_code=l.code,
            location_name=l.name,
            location_is_active=l.is_active,
            owner_id=p.owner_id,
            owner_name=None,
            lot_id=p.lot_id,
            lot_number=lot.number if lot else None,
            serial_id=p.serial_id,
            serial_number=serial.number if serial else None,
            stock_status=p.stock_status,
            base_uom=p.base_uom,
            manufactured_on=lot.manufactured_on if lot else None,
            expires_on=lot.expires_on if lot else None,
            on_hand_qty=p.on_hand_qty,
            version=p.version,
        )

    @staticmethod
    def details(
        p: P,
        l: L,
        w: W,
        item: I,
        lot: Lot | None,
        serial: S | None,
        ledger_quantity: Decimal,
    ) -> GetStockPositionResultDTO:
        """Создаёт собственный DTO сценария с точными количествами."""
        return GetStockPositionResultDTO(
            id=p.id,
            inventory_item_id=p.inventory_item_id,
            sku=item.sku,
            warehouse_id=w.id,
            warehouse_code=w.code,
            warehouse_name=w.name,
            warehouse_is_active=w.is_active,
            location_id=l.id,
            location_code=l.code,
            location_name=l.name,
            location_is_active=l.is_active,
            owner_id=p.owner_id,
            owner_name=None,
            lot_id=p.lot_id,
            lot_number=lot.number if lot else None,
            serial_id=p.serial_id,
            serial_number=serial.number if serial else None,
            stock_status=p.stock_status,
            base_uom=p.base_uom,
            manufactured_on=lot.manufactured_on if lot else None,
            expires_on=lot.expires_on if lot else None,
            on_hand_qty=p.on_hand_qty,
            version=p.version,
            ledger_quantity=ledger_quantity,
        )

    @staticmethod
    def movement(
        p: P,
        l: L,
        w: W,
        item: I,
        lot: Lot | None,
        serial: S | None,
        entry: Entry,
        posting: T,
        execution: E,
        document: D,
        line_ids: tuple[UUID, ...],
        historical_skus: tuple[str, ...],
        status_change: StatusDetails | None = None,
        return_details: ReturnDetails | None = None,
    ) -> ListStockMovementsItemDTO:
        """Создаёт собственный DTO сценария с точными количествами."""
        return ListStockMovementsItemDTO(
            id=entry.id,
            position_id=p.id,
            inventory_item_id=p.inventory_item_id,
            sku=item.sku,
            warehouse_id=w.id,
            warehouse_code=w.code,
            warehouse_name=w.name,
            warehouse_is_active=w.is_active,
            location_id=l.id,
            location_code=l.code,
            location_name=l.name,
            location_is_active=l.is_active,
            owner_id=p.owner_id,
            owner_name=None,
            lot_id=p.lot_id,
            lot_number=lot.number if lot else None,
            serial_id=p.serial_id,
            serial_number=serial.number if serial else None,
            stock_status=p.stock_status,
            base_uom=p.base_uom,
            manufactured_on=lot.manufactured_on if lot else None,
            expires_on=lot.expires_on if lot else None,
            document_id=document.id,
            execution_id=execution.id,
            posting_id=posting.id,
            document_status=document.status,
            operation_type=posting.operation_type,
            posted_at=posting.posted_at,
            quantity_delta=entry.quantity_delta,
            execution_line_ids=line_ids,
            historical_skus=historical_skus,
            return_direction=return_details.direction if return_details else None,
            origin_execution_id=(
                return_details.origin_execution_id if return_details else None
            ),
            write_off_reason=execution.write_off_reason,
            operation_reason=(
                return_details.reason
                if return_details
                else (
                    status_change.reason
                    if status_change
                    else execution.write_off_reason
                )
            ),
            target_status=status_change.target_status if status_change else None,
        )

    @staticmethod
    def balance(
        item: I,
        location: L,
        warehouse: W,
        lot: Lot | None,
        serial: S | None,
        owner: UUID,
        status: str,
        uom: str,
        quantity: Decimal,
        count: int,
        lot_count: int,
        serial_count: int,
        group_by_lot: bool,
        group_by_serial: bool,
    ) -> ListStockBalancesItemDTO:
        """Преобразует одну SQL-группу в сводный остаток без подмены её ID позиции."""
        return ListStockBalancesItemDTO(
            key=":".join(
                (
                    str(item.id),
                    str(warehouse.id),
                    str(location.id),
                    str(owner),
                    status,
                    uom,
                    str(group_by_lot),
                    str(lot.id) if lot else "-",
                    str(group_by_serial),
                    str(serial.id) if serial else "-",
                )
            ),
            inventory_item_id=item.id,
            sku=item.sku,
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            warehouse_is_active=warehouse.is_active,
            location_id=location.id,
            location_code=location.code,
            location_name=location.name,
            location_is_active=location.is_active,
            owner_id=owner,
            owner_name=None,
            lot_id=lot.id if lot else None,
            lot_number=lot.number if lot else None,
            serial_id=serial.id if serial else None,
            serial_number=serial.number if serial else None,
            stock_status=status,
            base_uom=uom,
            manufactured_on=lot.manufactured_on if lot else None,
            expires_on=lot.expires_on if lot else None,
            on_hand_qty=quantity,
            position_count=count,
            lot_count=lot_count,
            serial_count=serial_count,
        )
