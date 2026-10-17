from dataclasses import dataclass
from src.modules.identity.application.auth.port.session_store import SessionRecord


@dataclass(frozen=True, slots=True)
class CompleteCloudAuthResultDTO:
    purpose: str
    session: SessionRecord | None
