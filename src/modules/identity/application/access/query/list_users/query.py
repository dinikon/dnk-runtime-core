from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListUsersQuery:
    host: str
    session_token: str | None
