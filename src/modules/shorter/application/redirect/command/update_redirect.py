from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateRedirectCommand:
    redirect_id: UUID
    target_url: str
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_id: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    is_override: bool = False
    is_append: bool = False
