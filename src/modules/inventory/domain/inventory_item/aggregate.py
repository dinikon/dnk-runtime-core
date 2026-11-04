from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.inventory_item.availability_snapshot import (
    InventoryItemAvailabilitySnapshot,
)
from src.modules.inventory.domain.inventory_item.execution_snapshot import (
    InventoryItemExecutionSnapshot,
)
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.entity.item_packaging import (
    ItemPackaging,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.packaging_quantity import (
    PackagingQuantityVO,
)
from src.modules.inventory.domain.packaging_type.snapshot import PackagingTypeSnapshot
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.uom_catalog import get_compatible_uoms, get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_definition import UomDefinitionVO
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemValueError,
    InvalidTrackingConfigurationError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
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
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class InventoryItem:
    """Складская номенклатура с неизменяемыми настройками и дочерним составом."""

    id: InventoryItemIdVO
    sku: SkuVO
    base_uom: UomCodeVO
    quantity_rules: QuantityRulesVO
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    packagings: tuple[ItemPackaging, ...]
    barcodes: tuple[ItemBarcode, ...]

    @classmethod
    def create(
        cls,
        *,
        identifier: InventoryItemIdVO,
        sku: SkuVO,
        base_uom: UomCodeVO,
        quantity_rules: QuantityRulesVO,
        tracking_mode: TrackingMode = TrackingMode.NONE,
        expiration_mode: ExpirationMode = ExpirationMode.NONE,
        barcodes: tuple[ItemBarcode, ...] = (),
    ) -> Self:
        """Создаёт складской вариант с необязательными упаковками и штрихкодами."""
        return cls.restore(
            identifier=identifier,
            packagings=(),
            sku=sku,
            base_uom=base_uom,
            quantity_rules=quantity_rules,
            tracking_mode=tracking_mode,
            expiration_mode=expiration_mode,
            barcodes=barcodes,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: InventoryItemIdVO,
        sku: SkuVO,
        base_uom: UomCodeVO,
        quantity_rules: QuantityRulesVO,
        tracking_mode: TrackingMode,
        expiration_mode: ExpirationMode,
        packagings: tuple[ItemPackaging, ...],
        barcodes: tuple[ItemBarcode, ...],
    ) -> Self:
        """Восстанавливает полный состав и проверяет все инварианты агрегата."""
        item = cls(
            id=identifier,
            packagings=packagings,
            sku=sku,
            base_uom=base_uom,
            quantity_rules=quantity_rules,
            tracking_mode=tracking_mode,
            expiration_mode=expiration_mode,
            barcodes=barcodes,
        )
        item._validate()
        return item

    def change_sku(self, sku: SkuVO) -> Self:
        """Возвращает позицию с новым ручным SKU и прежней идентичностью."""
        return self._with_changes(sku=sku)

    def availability_snapshot(self) -> InventoryItemAvailabilitySnapshot:
        """Возвращает проверенные настройки количества, прослеживаемости и срока для доступности."""
        self._validate()
        return InventoryItemAvailabilitySnapshot(
            self.id,
            self.base_uom,
            self.quantity_rules,
            self.tracking_mode,
            self.expiration_mode,
        )

    def execution_snapshot(self) -> InventoryItemExecutionSnapshot:
        """Возвращает проверенные правила количества, прослеживаемости и дат для исполнения."""
        self._validate()
        return InventoryItemExecutionSnapshot(
            self.id,
            self.base_uom,
            self.quantity_rules,
            self.tracking_mode,
            self.expiration_mode,
        )

    def document_snapshot(self) -> InventoryItemDocumentSnapshot:
        """Возвращает проверенные идентичность, SKU и настройки планового количества."""
        self._validate()
        return InventoryItemDocumentSnapshot(
            self.id, self.sku, self.base_uom, self.quantity_rules, self.tracking_mode
        )

    def stock_snapshot(self) -> InventoryItemStockSnapshot:
        """Возвращает проверенные настройки количества и прослеживаемости без коллекций товара."""
        self._validate()
        return InventoryItemStockSnapshot(
            self.id, self.base_uom, self.quantity_rules, self.tracking_mode
        )

    def tracking_snapshot(self) -> InventoryItemTrackingSnapshot:
        """Возвращает только идентичность товара и настройки прослеживаемости."""
        return InventoryItemTrackingSnapshot(
            inventory_item_id=self.id,
            tracking_mode=self.tracking_mode,
            expiration_mode=self.expiration_mode,
        )

    def add_barcode(self, barcode: ItemBarcode) -> Self:
        """Добавляет идентификатор товара с проверкой уникальности внутри позиции."""
        return self._with_changes(barcodes=(*self.barcodes, barcode))

    def change_barcode(
        self,
        *,
        identifier: ItemBarcodeIdVO,
        barcode: BarcodeVO,
    ) -> Self:
        """Заменяет значения собственного штрихкода, сохраняя его идентификатор."""
        self._find_barcode(identifier)
        changed = ItemBarcode.create(identifier=identifier, barcode=barcode)
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

    @property
    def available_uoms(self) -> tuple[UomDefinitionVO, ...]:
        """Возвращает все единицы размерности товара без индивидуальных коэффициентов."""
        return get_compatible_uoms(self.base_uom)

    def to_base_quantity(self, *, quantity: QuantityVO, uom: UomCodeVO) -> QuantityVO:
        """Точно пересчитывает в базовую единицу и проверяет кратность шагу товара."""
        converted = UomConversionPolicy.convert(
            quantity=quantity, from_uom=uom, to_uom=self.base_uom
        )
        QuantityValidationPolicy.validate(quantity=converted, rules=self.quantity_rules)
        return converted

    def get_packaging(self, identifier: ItemPackagingIdVO) -> ItemPackaging:
        """Находит только собственный вариант упаковки товара."""
        for packaging in self.packagings:
            if packaging.id == identifier:
                return packaging
        raise InventoryItemComponentNotFoundError("Упаковка отсутствует в позиции.")

    def add_packaging(
        self, packaging: ItemPackaging, *, packaging_type: PackagingTypeSnapshot
    ) -> Self:
        """Добавляет пользовательский вариант активной тары с явно заданным содержимым."""
        if not isinstance(packaging, ItemPackaging):
            raise InvalidInventoryItemValueError("Ожидалась Entity ItemPackaging.")
        self._ensure_packaging_type(packaging_type)
        if packaging.packaging_type_id != packaging_type.id:
            raise InventoryItemConflictError(
                "Снимок типа тары не соответствует упаковке."
            )
        return self._with_changes(packagings=(*self.packagings, packaging))

    def change_packaging(
        self,
        *,
        identifier: ItemPackagingIdVO,
        packaging_type: PackagingTypeSnapshot,
        code: PackagingCodeVO,
        name: PackagingNameVO,
        content_quantity: PackagingQuantityVO,
        content_uom: UomCodeVO,
    ) -> Self:
        """Меняет содержимое или тип варианта упаковки с сохранением его ID."""
        self.get_packaging(identifier)
        self._ensure_packaging_type(packaging_type)
        changed = ItemPackaging.create(
            identifier=identifier,
            packaging_type_id=packaging_type.id,
            code=code,
            name=name,
            content_quantity=content_quantity,
            content_uom=content_uom,
        )
        return self._with_changes(
            packagings=tuple(
                changed if item.id == identifier else item for item in self.packagings
            )
        )

    def remove_packaging(self, identifier: ItemPackagingIdVO) -> Self:
        """Удаляет существующий вариант независимо от идентификаторов товара."""
        self.get_packaging(identifier)
        return self._with_changes(
            packagings=tuple(item for item in self.packagings if item.id != identifier)
        )

    @staticmethod
    def _ensure_packaging_type(packaging_type: PackagingTypeSnapshot) -> None:
        """Проверяет по снимку существующий контракт назначения тары без обращения к БД."""
        if (
            not isinstance(packaging_type, PackagingTypeSnapshot)
            or not isinstance(packaging_type.id, PackagingTypeIdVO)
            or not isinstance(packaging_type.code, PackagingCodeVO)
            or not isinstance(packaging_type.name, PackagingNameVO)
            or type(packaging_type.is_active) is not bool
        ):
            raise InvalidInventoryItemValueError("Нужен корректный снимок типа тары.")
        if not packaging_type.is_active:
            raise InventoryItemConflictError(
                "Неактивный тип тары нельзя назначить упаковке."
            )

    def _validate(self) -> None:
        """Проверяет типы, совместимость настроек и целостность дочернего состава."""
        if (
            not isinstance(self.id, InventoryItemIdVO)
            or not isinstance(self.sku, SkuVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity_rules, QuantityRulesVO)
            or not isinstance(self.tracking_mode, TrackingMode)
            or not isinstance(self.expiration_mode, ExpirationMode)
            or not isinstance(self.packagings, tuple)
            or not isinstance(self.barcodes, tuple)
        ):
            raise InvalidInventoryItemValueError(
                "Нужны типизированные значения и неизменяемые коллекции позиции."
            )
        if (
            self.tracking_mode is TrackingMode.NONE
            and self.expiration_mode.controls_expiration
        ):
            raise InvalidTrackingConfigurationError(
                "Обязательный срок годности требует учёта по партиям или сериям."
            )
        get_uom(self.base_uom)
        if self.tracking_mode.requires_serial and (
            self.base_uom != UomCodeVO("PCS")
            or self.quantity_rules.step != Decimal("1")
        ):
            raise InvalidTrackingConfigurationError(
                "Серийный учёт требует базовую единицу PCS и шаг 1."
            )
        for packaging in self.packagings:
            if not isinstance(packaging, ItemPackaging):
                raise InvalidInventoryItemValueError("Ожидалась Entity ItemPackaging.")
            packaging.ensure_valid()
        if len({item.id for item in self.packagings}) != len(self.packagings) or len(
            {item.code for item in self.packagings}
        ) != len(self.packagings):
            raise InventoryItemConflictError(
                "ID и коды упаковок товара должны быть уникальны."
            )
        for barcode in self.barcodes:
            if not isinstance(barcode, ItemBarcode):
                raise InvalidInventoryItemValueError("Ожидалась Entity ItemBarcode.")
            barcode.ensure_valid()
        if len({item.id for item in self.barcodes}) != len(self.barcodes) or len(
            {item.barcode for item in self.barcodes}
        ) != len(self.barcodes):
            raise InventoryItemConflictError(
                "ID и значения штрихкодов должны быть уникальны."
            )
        for packaging in self.packagings:
            self.to_base_quantity(
                quantity=QuantityVO(packaging.content_quantity.value),
                uom=packaging.content_uom,
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
