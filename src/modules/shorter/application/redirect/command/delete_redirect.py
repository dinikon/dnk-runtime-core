from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeleteRedirectCommand:
    redirect_id: UUID
