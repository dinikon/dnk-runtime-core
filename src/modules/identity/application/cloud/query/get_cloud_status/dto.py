from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetCloudStatusResultDTO:
    enabled: bool
    linked: bool
