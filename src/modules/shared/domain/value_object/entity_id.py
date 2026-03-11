from dataclasses import dataclass
from typing import Self
from uuid import UUID

import uuid6


@dataclass(frozen=True, slots=True)
class EntityIdVO:
    value: UUID

    @classmethod
    def new(cls) -> Self:
        return cls(value=uuid6.uuid7())

    @classmethod
    def from_value(cls, value: UUID | str) -> Self:
        if isinstance(value, str):
            value = UUID(value)
        return cls(value=value)

    def __str__(self) -> str:
        return str(self.value)
