from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateInvitationResultDTO:
    id: UUID
    email: str
    role: str
    state: str
    expires_at: datetime
    invitation_url: str
