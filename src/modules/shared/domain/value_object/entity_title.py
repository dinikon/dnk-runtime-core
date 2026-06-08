from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityTitleVO:
    value: str

    MAX_LENGTH = 255

    def __post_init__(self) -> None:
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"EntityTitleVO value must be no longer than {self.MAX_LENGTH} characters"
            )
