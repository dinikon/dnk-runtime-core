from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.shorter.domain.redirect import RedirectEntity


@dataclass(frozen=True, slots=True)
class RedirectDTO:
    redirect_id: UUID
    created_at: datetime
    updated_at: datetime
    target_url: str
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_id: str | None
    utm_term: str | None
    utm_content: str | None
    is_override: bool
    is_append: bool

    @classmethod
    def from_entity(cls, redirect: RedirectEntity) -> "RedirectDTO":
        return cls(
            redirect_id=redirect.id.value,
            created_at=redirect.created_at,
            updated_at=redirect.updated_at,
            target_url=redirect.target_url.value,
            utm_source=redirect.utm_parameters.utm_source,
            utm_medium=redirect.utm_parameters.utm_medium,
            utm_campaign=redirect.utm_parameters.utm_campaign,
            utm_id=redirect.utm_parameters.utm_id,
            utm_term=redirect.utm_parameters.utm_term,
            utm_content=redirect.utm_parameters.utm_content,
            is_override=redirect.is_override,
            is_append=redirect.is_append,
        )
