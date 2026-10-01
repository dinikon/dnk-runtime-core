from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StartCloudAuthCommand:
    host: str
    session_token: str | None
    flow_cookie: str | None
    purpose: str
