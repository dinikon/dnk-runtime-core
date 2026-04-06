from dataclasses import dataclass

from src.modules.schema_registry.domain.error import InvalidFieldOperationError
from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.enum.field_type_mode import (
    FieldTypeModeEnum,
)


@dataclass(frozen=True, slots=True)
class FieldTypeVO:
    code: FieldTypeEnum
    mode: FieldTypeModeEnum
    literal_value: str | None = None

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
        )

    @classmethod
    def sql(cls, code: FieldTypeEnum) -> "FieldTypeVO":
        return cls(
            code=code,
            mode=FieldTypeModeEnum.SQL,
            literal_value=None,
        )

    def is_select_like(self) -> bool:
        return self.code in {FieldTypeEnum.SELECT, FieldTypeEnum.MULTISELECT}
