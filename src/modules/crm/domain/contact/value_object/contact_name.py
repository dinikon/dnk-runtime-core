from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ContactNameVO:
    last_name: str
    first_name: str | None
    middle_name: str | None

    def __post_init__(self) -> None:
        if not self.last_name:
            raise ValueError("last_name cannot be empty")
