from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateBroadcastCommand:

    title: str
    description: str
