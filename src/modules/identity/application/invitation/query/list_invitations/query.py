from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListInvitationsQuery:
    host: str
    session_token: str | None
