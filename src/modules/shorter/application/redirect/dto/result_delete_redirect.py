from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResultDeleteRedirectDTO:
    redirect_id: UUID
