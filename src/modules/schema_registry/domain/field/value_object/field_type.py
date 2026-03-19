from dataclasses import dataclass

from src.modules.schema_registry.domain.error import InvalidFieldOperationError
from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.enum.field_type_mode import (
    FieldTypeModeEnum,
)
from src.modules.schema_registry.domain.field.enum.sql_type_preset import (
    SqlTypePresetEnum,
)


@dataclass(frozen=True, slots=True)
class FieldTypeVO:
    code: FieldTypeEnum
    mode: FieldTypeModeEnum
    literal_value: str | None = None
    sql_preset: SqlTypePresetEnum | None = None

    @classmethod
    def literal(cls, code: FieldTypeEnum, literal_value: str) -> "FieldTypeVO":
        if not literal_value or not literal_value.strip():
            raise InvalidFieldOperationError(
                "Literal field type value cannot be empty."
            )
        return cls(
            code=code,
            mode=FieldTypeModeEnum.LITERAL,
            literal_value=literal_value.strip(),
            sql_preset=None,
        )

    @classmethod
    def sql(cls, code: FieldTypeEnum, sql_preset: SqlTypePresetEnum) -> "FieldTypeVO":
        return cls(
            code=code,
            mode=FieldTypeModeEnum.SQL,
            literal_value=None,
            sql_preset=sql_preset,
        )

    def is_select_like(self) -> bool:
        return self.code in {FieldTypeEnum.SELECT, FieldTypeEnum.MULTISELECT}
