from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompleteCloudAuthCommand:
    host: str
    session_token: str | None
    flow_cookie: str | None
    state: str
    code: str
    issuer: str
    error: str | None = None
