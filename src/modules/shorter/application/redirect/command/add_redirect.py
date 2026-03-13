from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AddRedirectCommand:
    target_url: str
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_id: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    is_override: bool = False
    is_append: bool = False
