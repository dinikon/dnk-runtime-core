from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CloudIdentity:
    user_id: UUID
    issuer: str
    subject: str
