from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from ..errors import (
    DataSourceDsnInvalidError,
    DataSourceSchemaInvalidFormatError,
    DataSourceSchemaRequiredError,
    DataSourceTypeNotSupportedError,
)
from modules.shared.domain.value_object.entity_id import EntityIdVO


class DataSourceIdVO(EntityIdVO): ...


class DataSourceTypeVO(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"

    @classmethod
    def from_value(cls, value: str | DataSourceTypeVO) -> DataSourceTypeVO:
        if isinstance(value, cls):
            return value

        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            raise DataSourceTypeNotSupportedError(value) from None


@dataclass(frozen=True, slots=True)
class DataSourceSchemaVO:
    value: str

    _SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
    _MAX_LENGTH = 63

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise DataSourceSchemaRequiredError()
        if len(normalized) > self._MAX_LENGTH:
            raise DataSourceSchemaInvalidFormatError(self.value)
        if not self._SCHEMA_PATTERN.match(normalized):
            raise DataSourceSchemaInvalidFormatError(self.value)
        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_value(cls, value: str | DataSourceSchemaVO) -> DataSourceSchemaVO:
        if isinstance(value, cls):
            return value
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DataSourceDsnVO:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise DataSourceDsnInvalidError(self.value)
        parsed = urlparse(normalized)
        if not parsed.scheme:
            raise DataSourceDsnInvalidError(self.value)

        if parsed.scheme == DataSourceTypeVO.SQLITE:
            if not parsed.path:
                raise DataSourceDsnInvalidError(self.value)
        elif not parsed.netloc:
            raise DataSourceDsnInvalidError(self.value)

        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_value(cls, value: str | DataSourceDsnVO) -> DataSourceDsnVO:
        if isinstance(value, cls):
            return value
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


__all__ = [
    "DataSourceDsnVO",
    "DataSourceIdVO",
    "DataSourceSchemaVO",
    "DataSourceTypeVO",
]
