from src.modules.inventory.application.inventory_item.command.update_inventory_item.command import (
    UpdateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.dto import (
    UpdatedInventoryItemBarcodeDTO,
    UpdateInventoryItemResultDTO,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.error import (
    InvalidInventoryItemUpdateError,
)
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class UpdateInventoryItemHandler:
    """Координирует обновление полного агрегата в общей транзакции."""

    def __init__(
        self,
        repository: InventoryItemRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает write-порт и генератор ID новых штрихкодов."""
        self._repository = repository
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: UpdateInventoryItemCommand
    ) -> UpdateInventoryItemResultDTO:
        """Загружает под блокировкой и делегирует согласованный переход Domain."""
        values = {
            "sku": command.sku,
            "base_uom": command.base_uom,
            "quantity_rules": command.quantity_step,
            "tracking_mode": command.tracking_mode,
            "expiration_mode": command.expiration_mode,
            "barcodes": command.barcodes,
        }
        if (
            not isinstance(command.fields, frozenset)
            or not command.fields
            or not command.fields <= values.keys()
            or any(values[name] is None for name in command.fields)
            or (
                "barcodes" in command.fields and not isinstance(command.barcodes, tuple)
            )
        ):
            raise InvalidInventoryItemUpdateError(
                "Нужен непустой набор известных полей без null."
            )
        item = await self._repository.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        barcodes = item.barcodes
        if "barcodes" in command.fields:
            existing = {child.barcode: child for child in item.barcodes}
            requested = tuple(BarcodeVO(value) for value in command.barcodes)
            barcodes = tuple(
                (
                    existing[code]
                    if code in existing
                    else ItemBarcode.create(
                        identifier=ItemBarcodeIdVO.from_value(
                            self._uuid_generator.new()
                        ),
                        barcode=code,
                    )
                )
                for code in requested
            )
        updated = item.revise(
            sku=SkuVO(command.sku) if "sku" in command.fields else item.sku,
            base_uom=(
                UomCodeVO(command.base_uom)
                if "base_uom" in command.fields
                else item.base_uom
            ),
            quantity_rules=(
                QuantityRulesVO(command.quantity_step)
                if "quantity_rules" in command.fields
                else item.quantity_rules
            ),
            tracking_mode=(
                command.tracking_mode
                if "tracking_mode" in command.fields
                else item.tracking_mode
            ),
            expiration_mode=(
                command.expiration_mode
                if "expiration_mode" in command.fields
                else item.expiration_mode
            ),
            barcodes=barcodes,
        )
        if updated is not item:
            await self._repository.save(updated)
        return UpdateInventoryItemResultDTO(
            id=updated.id.uuid,
            sku=updated.sku.value,
            base_uom=updated.base_uom.value,
            quantity_step=updated.quantity_rules.step,
            tracking_mode=updated.tracking_mode,
            expiration_mode=updated.expiration_mode,
            barcodes=tuple(
                UpdatedInventoryItemBarcodeDTO(child.id.uuid, child.barcode.value)
                for child in updated.barcodes
            ),
        )
