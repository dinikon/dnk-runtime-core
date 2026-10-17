from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetCloudStatusQuery:
    host: str
    session_token: str | None
