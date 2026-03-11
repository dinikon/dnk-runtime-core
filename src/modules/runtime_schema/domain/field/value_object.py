from enum import StrEnum

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


class FieldName: ...
