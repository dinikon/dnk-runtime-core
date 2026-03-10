from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PersonName:
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None

    def __post_init__(self) -> None:
        first_name = self.first_name.strip()
        if not first_name:
            raise ValueError("first_name cannot be empty")

        last_name = self.last_name.strip() if self.last_name else None
        middle_name = self.middle_name.strip() if self.middle_name else None

        object.__setattr__(self, "first_name", first_name)
        object.__setattr__(self, "last_name", last_name or None)
        object.__setattr__(self, "middle_name", middle_name or None)

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(part for part in parts if part)


__all__ = ["PersonName"]

