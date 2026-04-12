from dataclasses import dataclass

from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum


@dataclass(frozen=True, slots=True)
class FieldTypeVO:
    """Value object для доменного типа поля."""

    code: FieldTypeEnum

    @classmethod
    def sql(cls, code: FieldTypeEnum) -> "FieldTypeVO":
        """Создает field type для SQL-backed runtime-поля."""
        return cls(code=code)

    def is_select_like(self) -> bool:
        """Проверяет, поддерживает ли тип options из seed/spec."""
        return self.code in {FieldTypeEnum.SELECT, FieldTypeEnum.MULTISELECT}
