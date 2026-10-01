from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChangeUserAccessResultDTO:
    ok: bool = True
