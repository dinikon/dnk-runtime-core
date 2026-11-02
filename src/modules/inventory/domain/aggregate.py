from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.entity.item_uom_conversion import ItemUomConversion
from src.modules.inventory.domain.error import (
    InvalidInventoryItemValueError,
    InvalidTrackingConfigurationError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
    UnknownUomError,
)
from src.modules.inventory.domain.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.value_object.conversion_factor import (
    ConversionFactorVO,
)
from src.modules.inventory.domain.value_object.expiration_mode import ExpirationMode
from src.modules.inventory.domain.value_object.identifier import InventoryItemIdVO
from src.modules.inventory.domain.value_object.item_barcode_id import ItemBarcodeIdVO
from src.modules.inventory.domain.value_object.item_uom_conversion_id import (
    ItemUomConversionIdVO,
)
from src.modules.inventory.domain.value_object.sku import SkuVO
from src.modules.inventory.domain.value_object.tracking_mode import TrackingMode
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class InventoryItem:
    """Складская номенклатура с неизменяемыми настройками и дочерним составом."""

    id: InventoryItemIdVO
    sku: SkuVO
    base_uom: UomCodeVO
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: tuple[ItemBarcode, ...]
    uom_conversions: tuple[ItemUomConversion, ...]

    @classmethod
    def create(
        cls,
        *,
        identifier: InventoryItemIdVO,
        sku: SkuVO,
        base_uom: UomCodeVO,
        tracking_mode: TrackingMode = TrackingMode.NONE,
        expiration_mode: ExpirationMode = ExpirationMode.DISABLED,
        barcodes: tuple[ItemBarcode, ...] = (),
        uom_conversions: tuple[ItemUomConversion, ...] = (),
    ) -> Self:
        """Создаёт позицию с ручным SKU и проверенным составом без генерации значений."""
        return cls.restore(
            identifier=identifier,
            sku=sku,
            base_uom=base_uom,
            tracking_mode=tracking_mode,
            expiration_mode=expiration_mode,
            barcodes=barcodes,
            uom_conversions=uom_conversions,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: InventoryItemIdVO,
        sku: SkuVO,
        base_uom: UomCodeVO,
        tracking_mode: TrackingMode,
        expiration_mode: ExpirationMode,
        barcodes: tuple[ItemBarcode, ...],
        uom_conversions: tuple[ItemUomConversion, ...],
    ) -> Self:
        """Восстанавливает полный состав и проверяет все инварианты агрегата."""
        item = cls(
            id=identifier,
            sku=sku,
            base_uom=base_uom,
            tracking_mode=tracking_mode,
            expiration_mode=expiration_mode,
            barcodes=barcodes,
            uom_conversions=uom_conversions,
        )
        item._validate()
        return item

    def change_sku(self, sku: SkuVO) -> Self:
        """Возвращает позицию с новым ручным SKU и прежней идентичностью."""
        return self._with_changes(sku=sku)

    def add_barcode(self, barcode: ItemBarcode) -> Self:
        """Добавляет штрихкод с проверкой уникальности и объявленной единицы."""
        return self._with_changes(barcodes=(*self.barcodes, barcode))

    def change_barcode(
        self, *, identifier: ItemBarcodeIdVO, barcode: BarcodeVO, uom: UomCodeVO
    ) -> Self:
        """Заменяет значения собственного штрихкода, сохраняя его идентификатор."""
        self._find_barcode(identifier)
        changed = ItemBarcode.create(identifier=identifier, barcode=barcode, uom=uom)
        return self._with_changes(
            barcodes=tuple(
                changed if item.id == identifier else item for item in self.barcodes
            )
        )

    def remove_barcode(self, identifier: ItemBarcodeIdVO) -> Self:
        """Удаляет только существующий штрихкод данной позиции."""
        self._find_barcode(identifier)
        return self._with_changes(
            barcodes=tuple(item for item in self.barcodes if item.id != identifier)
        )

    def add_uom_conversion(self, conversion: ItemUomConversion) -> Self:
        """Добавляет прямую конвертацию дополнительной единицы в базовую."""
        return self._with_changes(uom_conversions=(*self.uom_conversions, conversion))

    def change_uom_conversion(
        self,
        *,
        identifier: ItemUomConversionIdVO,
        uom: UomCodeVO,
        factor: ConversionFactorVO,
    ) -> Self:
        """Заменяет собственную конвертацию с проверкой всех зависимых штрихкодов."""
        self._find_uom_conversion(identifier)
        changed = ItemUomConversion.create(
            identifier=identifier, uom=uom, factor=factor
        )
        return self._with_changes(
            uom_conversions=tuple(
                changed if item.id == identifier else item
                for item in self.uom_conversions
            )
        )

    def remove_uom_conversion(self, identifier: ItemUomConversionIdVO) -> Self:
        """Удаляет конвертацию только при отсутствии использующих её штрихкодов."""
        conversion = self._find_uom_conversion(identifier)
        if any(item.uom == conversion.uom for item in self.barcodes):
            raise InventoryItemConflictError(
                "Единица конвертации используется штрихкодом."
            )
        return self._with_changes(
            uom_conversions=tuple(
                item for item in self.uom_conversions if item.id != identifier
            )
        )

    def _validate(self) -> None:
        """Проверяет типы, совместимость настроек и целостность дочернего состава."""
        if (
            not isinstance(self.id, InventoryItemIdVO)
            or not isinstance(self.sku, SkuVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.tracking_mode, TrackingMode)
            or not isinstance(self.expiration_mode, ExpirationMode)
            or not isinstance(self.barcodes, tuple)
            or not isinstance(self.uom_conversions, tuple)
        ):
            raise InvalidInventoryItemValueError(
                "Нужны типизированные значения и неизменяемые коллекции позиции."
            )
        if (
            self.tracking_mode is TrackingMode.NONE
            and self.expiration_mode is ExpirationMode.REQUIRED
        ):
            raise InvalidTrackingConfigurationError(
                "Обязательный срок годности требует учёта по партиям или сериям."
            )
        for barcode in self.barcodes:
            if not isinstance(barcode, ItemBarcode):
                raise InvalidInventoryItemValueError("Ожидалась Entity ItemBarcode.")
            barcode.ensure_valid()
        for conversion in self.uom_conversions:
            if not isinstance(conversion, ItemUomConversion):
                raise InvalidInventoryItemValueError(
                    "Ожидалась Entity ItemUomConversion."
                )
            conversion.ensure_valid()
        if (
            len({item.id for item in self.barcodes}) != len(self.barcodes)
            or len({item.barcode for item in self.barcodes}) != len(self.barcodes)
            or len({item.id for item in self.uom_conversions})
            != len(self.uom_conversions)
            or len({item.uom for item in self.uom_conversions})
            != len(self.uom_conversions)
        ):
            raise InventoryItemConflictError(
                "Штрихкоды, единицы конвертации и ID внутри коллекций должны быть уникальны."
            )
        units = {item.uom for item in self.uom_conversions}
        if self.base_uom in units:
            raise InventoryItemConflictError(
                "Конвертация базовой единицы в саму себя запрещена."
            )
        units.add(self.base_uom)
        if any(item.uom not in units for item in self.barcodes):
            raise UnknownUomError(
                "Единица штрихкода должна быть базовой или иметь прямую конвертацию."
            )

    def _with_changes(self, **changes: object) -> Self:
        """Проверяет новый кандидат целиком, сохраняя исходный агрегат при отказе."""
        candidate = replace(self, **changes)
        candidate._validate()
        return candidate

    def _find_barcode(self, identifier: ItemBarcodeIdVO) -> ItemBarcode:
        """Находит штрихкод только среди собственных дочерних Entity."""
        for barcode in self.barcodes:
            if barcode.id == identifier:
                return barcode
        raise InventoryItemComponentNotFoundError("Штрихкод отсутствует в позиции.")

    def _find_uom_conversion(
        self, identifier: ItemUomConversionIdVO
    ) -> ItemUomConversion:
        """Находит конвертацию только среди собственных дочерних Entity."""
        for conversion in self.uom_conversions:
            if conversion.id == identifier:
                return conversion
        raise InventoryItemComponentNotFoundError("Конвертация отсутствует в позиции.")
