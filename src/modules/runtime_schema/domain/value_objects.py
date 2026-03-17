from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import Pattern, compile as re_compile
from uuid import UUID

from src.modules.runtime_schema.domain.errors import (
    InvalidDataSourceSchemaError,
    InvalidDataSourceTypeError,
    InvalidFieldNameError,
    InvalidFieldTypeError,
    InvalidObjectOwnershipKindError,
)

FIELD_NAME_MAX_LENGTH = 63
_FIELD_NAME_PATTERN: Pattern[str] = re_compile(
    rf"^[a-z][a-z0-9_]{{0,{FIELD_NAME_MAX_LENGTH - 1}}}$"
)


def normalize_required_text(value: str) -> str:
    return value.strip()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


class DataSourceType(StrEnum):
    POSTGRESQL = "postgresql"

    @classmethod
    def parse(cls, value: DataSourceType | str) -> DataSourceType:
        if isinstance(value, cls):
            parsed = value
        else:
            normalized = str(value).strip()
            try:
                parsed = cls(normalized)
            except ValueError as exc:
                raise InvalidDataSourceTypeError(str(value)) from exc

        if parsed is not cls.POSTGRESQL:
            raise InvalidDataSourceTypeError(str(value))

        return parsed


class ObjectOwnershipKind(StrEnum):
    MODULE = "module"
    CUSTOM = "custom"

    @classmethod
    def parse(
        cls,
        value: ObjectOwnershipKind | str,
    ) -> ObjectOwnershipKind:
        if isinstance(value, cls):
            return value

        normalized = str(value).strip()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise InvalidObjectOwnershipKindError(str(value)) from exc


class FieldType(StrEnum):
    PK = "PK"
    STRING = "STRING"
    LARGE_TEXT = "LARGE_TEXT"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    SELECT = "SELECT"
    MULTISELECT = "MULTISELECT"

    @classmethod
    def parse(cls, value: FieldType | str) -> FieldType:
        if isinstance(value, cls):
            return value

        normalized = str(value).strip()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise InvalidFieldTypeError(str(value)) from exc


@dataclass(frozen=True, slots=True)
class DataSourceSchemaVO:
    value: str

    def __post_init__(self) -> None:
        normalized = normalize_required_text(str(self.value))

        try:
            UUID(normalized)
        except ValueError as exc:
            raise InvalidDataSourceSchemaError(self.value) from exc

        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class FieldNameVO:
    value: str

    def __post_init__(self) -> None:
        normalized = normalize_required_text(str(self.value))
        if not _FIELD_NAME_PATTERN.fullmatch(normalized):
            raise InvalidFieldNameError(self.value)
        object.__setattr__(self, "value", normalized)


__all__ = [
    "DataSourceSchemaVO",
    "DataSourceType",
    "FIELD_NAME_MAX_LENGTH",
    "FieldNameVO",
    "FieldType",
    "ObjectOwnershipKind",
    "normalize_optional_text",
    "normalize_required_text",
]
