from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StartCloudAuthResultDTO:
    authorization_url: str
