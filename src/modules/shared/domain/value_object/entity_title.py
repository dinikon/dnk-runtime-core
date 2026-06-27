from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class EntityTitleVO:
    value: str

    MAX_LENGTH: ClassVar[int] = 255

    def __post_init__(self) -> None:
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"EntityTitleVO value must be no longer than {self.MAX_LENGTH} characters"
            )
