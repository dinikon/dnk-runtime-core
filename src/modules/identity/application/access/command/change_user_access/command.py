from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangeUserAccessCommand:
    host: str
    session_token: str | None
    user_id: UUID
    role: str | None = None
    status: str | None = None
