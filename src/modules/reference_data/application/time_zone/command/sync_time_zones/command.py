from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncTimeZonesCommand:
    pass
