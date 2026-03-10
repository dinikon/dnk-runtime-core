from dataclasses import dataclass
from typing import Self
from uuid import UUID

import uuid6

from src.modules.crm.domain.error import LeadTitleRequiredError


@dataclass(frozen=True, slots=True)
class LeadId:
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


@dataclass(frozen=True, slots=True)
class LeadTitle:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise LeadTitleRequiredError()
        object.__setattr__(self, "value", normalized)

