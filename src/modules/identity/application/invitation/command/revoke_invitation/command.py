from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RevokeInvitationCommand:
    host: str
    session_token: str | None
    invitation_id: UUID
