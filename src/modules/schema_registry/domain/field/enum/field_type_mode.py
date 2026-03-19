from enum import Enum


class FieldTypeModeEnum(str, Enum):
    LITERAL = "literal"
    SQL = "sql"
