from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class EntityDescriptionVO:
    value: str

    MAX_LENGTH: ClassVar[int] = 1000

    def __post_init__(self) -> None:
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"EntityDescriptionVO value must be no longer than {self.MAX_LENGTH} characters"
            )

    @classmethod
    def optional(cls, value: str | None) -> "Description | None":
        if value is None or not value.strip():
            return None

        return cls(value)

    def __str__(self) -> str:
        return self.value
