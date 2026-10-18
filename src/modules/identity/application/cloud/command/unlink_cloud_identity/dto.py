from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnlinkCloudIdentityResultDTO:
    ok: bool = True
