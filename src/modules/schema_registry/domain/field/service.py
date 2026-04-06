from __future__ import annotations

from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.enum.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.schema_registry.domain.error import SeedValidationError


class FieldTypeService:
    def from_seed_type(self, raw_type: str) -> FieldTypeVO:
        normalized = raw_type.strip().lower()

        mapping = {
            FieldTypeEnum.UUID.value: FieldTypeVO.sql(
                FieldTypeEnum.UUID,
                SqlTypePresetEnum.UUID,
            ),
            FieldTypeEnum.TEXT.value: FieldTypeVO.sql(
                FieldTypeEnum.TEXT,
                SqlTypePresetEnum.TEXT,
            ),
            FieldTypeEnum.INT.value: FieldTypeVO.sql(
                FieldTypeEnum.INT,
                SqlTypePresetEnum.INTEGER,
            ),
            FieldTypeEnum.DECIMAL.value: FieldTypeVO.sql(
                FieldTypeEnum.DECIMAL,
                SqlTypePresetEnum.NUMERIC_14_2,
            ),
            FieldTypeEnum.BOOL.value: FieldTypeVO.sql(
                FieldTypeEnum.BOOL,
                SqlTypePresetEnum.BOOLEAN,
            ),
            FieldTypeEnum.DATE.value: FieldTypeVO.sql(
                FieldTypeEnum.DATE,
                SqlTypePresetEnum.DATE,
            ),
            FieldTypeEnum.DATETIME.value: FieldTypeVO.sql(
                FieldTypeEnum.DATETIME,
                SqlTypePresetEnum.TIMESTAMP,
            ),
            FieldTypeEnum.JSON.value: FieldTypeVO.sql(
                FieldTypeEnum.JSON,
                SqlTypePresetEnum.JSONB,
            ),
            FieldTypeEnum.SELECT.value: FieldTypeVO.sql(
                FieldTypeEnum.SELECT,
                SqlTypePresetEnum.TEXT,
            ),
            FieldTypeEnum.MULTISELECT.value: FieldTypeVO.sql(
                FieldTypeEnum.MULTISELECT,
                SqlTypePresetEnum.JSONB,
            ),
        }

        try:
            return mapping[normalized]
        except KeyError as exc:
            raise SeedValidationError(f"Unsupported seed field type '{raw_type}'.") from exc
