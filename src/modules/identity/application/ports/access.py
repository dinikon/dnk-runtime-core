from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CloudIdentity:
    user_id: UUID
    issuer: str
    subject: str


@dataclass(frozen=True)
class Invitation:
    id: UUID
    email: str
    role: str
    token_hash: str
    state: str
    created_by: UUID
    accepted_by: UUID | None
    created_at: datetime
    expires_at: datetime
