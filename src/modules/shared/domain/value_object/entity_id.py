from dataclasses import dataclass
from typing import Self
from uuid import UUID

import uuid6


@dataclass(frozen=True, slots=True)
class EntityIdVO:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("EntityIdVO value must be UUID")

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
