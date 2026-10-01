from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateInvitationCommand:
    host: str
    session_token: str | None
    email: str
    role: str
