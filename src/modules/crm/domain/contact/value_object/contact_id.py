from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ContactIdVO:
    value: EntityIdVO

    @classmethod
    def from_value(cls, value: UUID | str | EntityIdVO) -> "ContactIdVO":
        if isinstance(value, EntityIdVO):
            return cls(value=value)
        return cls(value=EntityIdVO.from_value(value))

    def __str__(self) -> str:
        return str(self.value)

    @property
    def uuid(self) -> UUID:
        return self.value.value
