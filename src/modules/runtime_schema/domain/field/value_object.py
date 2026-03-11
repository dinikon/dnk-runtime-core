import re
from dataclasses import dataclass
from enum import StrEnum

from ..errors import (
    FieldNameInvalidFormatError,
    FieldNameRequiredError,
)
from modules.shared.domain.value_object.entity_id import EntityIdVO


class FieldIdVO(EntityIdVO): ...


class FieldTypeVO(StrEnum):
    """
    Описывает системные поля, как обычные, примитивные типы, так и составные.
    """

    UUID = "uuid"
    STRING = "string"
    TEXT = "text"

    INTEGER = "integer"

    BOOLEAN = "boolean"
    DATE_TIME = "date_time"
    JSON = "json"

    SELECT = "select"
    MULTI_SELECT = "multi_select"
    RELATION = "relation"


@dataclass(frozen=True, slots=True)
class FieldName:
    value: str

    _SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise FieldNameRequiredError()
        if not self._SNAKE_CASE_PATTERN.match(normalized):
            raise FieldNameInvalidFormatError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


__all__ = ["FieldIdVO", "FieldName", "FieldTypeVO"]
