from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass(frozen=True, slots=True)
class InvitationViewDTO:
    id: UUID
    email: str
    role: str
    state: str
    expires_at: datetime
