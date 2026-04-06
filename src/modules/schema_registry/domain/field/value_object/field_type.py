from dataclasses import dataclass

from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum


@dataclass(frozen=True, slots=True)
class FieldTypeVO:
    code: FieldTypeEnum

    @classmethod
    def sql(cls, code: FieldTypeEnum) -> "FieldTypeVO":
        return cls(code=code)

    def is_select_like(self) -> bool:
        return self.code in {FieldTypeEnum.SELECT, FieldTypeEnum.MULTISELECT}
