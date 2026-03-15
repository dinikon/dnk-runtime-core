import uuid
from dataclasses import dataclass, field
from typing import Self
from uuid import UUID

from src.modules.runtime_schema.domain.schema.error import InvalidSchemaIdError


@dataclass(frozen=True, slots=True)
class SchemaIdVO:
    value: UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidSchemaIdError(self.value)

    @classmethod
    def from_value(cls, value: UUID | str) -> Self:
        if isinstance(value, UUID):
            return cls(value=value)
        if isinstance(value, str):
            try:
                return cls(value=UUID(value))
            except (TypeError, ValueError):
                raise InvalidSchemaIdError(value) from None
        raise InvalidSchemaIdError(value)

    def __str__(self) -> str:
        return str(self.value)
