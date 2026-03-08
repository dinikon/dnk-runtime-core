from enum import StrEnum


class RuntimeSchemaRelationOnDelete(StrEnum):
    RESTRICT = "restrict"
    SET_NULL = "set_null"
    CASCADE = "cascade"
