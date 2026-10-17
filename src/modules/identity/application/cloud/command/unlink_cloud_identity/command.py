from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnlinkCloudIdentityCommand:
    host: str
    session_token: str | None
