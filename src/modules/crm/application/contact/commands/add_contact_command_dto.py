from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AddContactCommandDTO:
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
