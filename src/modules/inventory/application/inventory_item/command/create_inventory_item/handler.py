from typing import TypedDict

from src.modules.inventory.application.inventory_item.command.create_inventory_item.command import (
    CreateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.create_inventory_item.dto import (
    CreatedInventoryItemBarcodeDTO,
    CreateInventoryItemResultDTO,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class _InventoryItemCreateSettings(TypedDict, total=False):
    """Типизирует только явно переданные фабрике Domain настройки создания."""

    base_uom: UomCodeVO
    quantity_rules: QuantityRulesVO
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode


class CreateInventoryItemHandler:
    """Создаёт проверенный агрегат и передаёт его порту записи."""

    def __init__(
        self,
        repository: InventoryItemRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает write-порт текущего UoW и генератор идентификаторов."""
        self._repository = repository
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: CreateInventoryItemCommand
    ) -> CreateInventoryItemResultDTO:
        """Создаёт позицию со штрихкодами; транзакцию завершает внешняя сборка."""
        identifier = InventoryItemIdVO.from_value(self._uuid_generator.new())
        barcodes = tuple(
            ItemBarcode.create(
                identifier=ItemBarcodeIdVO.from_value(self._uuid_generator.new()),
                barcode=BarcodeVO(value),
            )
            for value in command.barcodes
        )
        settings: _InventoryItemCreateSettings = {}
        if command.base_uom is not None:
            settings["base_uom"] = UomCodeVO(command.base_uom)
        if command.quantity_step is not None:
            settings["quantity_rules"] = QuantityRulesVO(command.quantity_step)
        if command.tracking_mode is not None:
            settings["tracking_mode"] = command.tracking_mode
        if command.expiration_mode is not None:
            settings["expiration_mode"] = command.expiration_mode
        item = InventoryItem.create(
            identifier=identifier,
            sku=SkuVO(command.sku),
            barcodes=barcodes,
            **settings,
        )
        await self._repository.add(item)
        return CreateInventoryItemResultDTO(
            id=item.id.uuid,
            sku=item.sku.value,
            base_uom=item.base_uom.value,
            quantity_step=item.quantity_rules.step,
            tracking_mode=item.tracking_mode,
            expiration_mode=item.expiration_mode,
            barcodes=tuple(
                CreatedInventoryItemBarcodeDTO(child.id.uuid, child.barcode.value)
                for child in item.barcodes
            ),
        )
