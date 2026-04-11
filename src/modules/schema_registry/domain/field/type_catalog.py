from __future__ import annotations

from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO


class FieldTypeCatalog:
    _SUPPORTED_TYPES = {
        FieldTypeEnum.UUID.value: FieldTypeEnum.UUID,
        FieldTypeEnum.TEXT.value: FieldTypeEnum.TEXT,
        FieldTypeEnum.INT.value: FieldTypeEnum.INT,
        FieldTypeEnum.DECIMAL.value: FieldTypeEnum.DECIMAL,
        FieldTypeEnum.BOOL.value: FieldTypeEnum.BOOL,
        FieldTypeEnum.DATE.value: FieldTypeEnum.DATE,
        FieldTypeEnum.DATETIME.value: FieldTypeEnum.DATETIME,
        FieldTypeEnum.JSON.value: FieldTypeEnum.JSON,
        FieldTypeEnum.SELECT.value: FieldTypeEnum.SELECT,
        FieldTypeEnum.MULTISELECT.value: FieldTypeEnum.MULTISELECT,
    }

    def from_seed_type(self, raw_type: str) -> FieldTypeVO:
        normalized = raw_type.strip().lower()
        try:
            field_type = self._SUPPORTED_TYPES[normalized]
        except KeyError as exc:
            raise SeedValidationError(
                f"Unsupported seed field type '{raw_type}'."
            ) from exc
        return FieldTypeVO.sql(field_type)

    def supported_seed_types(self) -> frozenset[str]:
        return frozenset(self._SUPPORTED_TYPES)
