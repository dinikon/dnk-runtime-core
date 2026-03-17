from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.crm.domain.value_objects import (
    normalize_company_last_name,
    normalize_company_name,
    normalize_contact_first_name,
    normalize_contact_last_name,
    normalize_contact_middle_name,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ContactEntity:
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    first_name: str
    middle_name: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "last_name", normalize_contact_last_name(self.last_name))
        object.__setattr__(
            self,
            "first_name",
            normalize_contact_first_name(self.first_name),
        )
        object.__setattr__(
            self,
            "middle_name",
            normalize_contact_middle_name(self.middle_name),
        )

    @classmethod
    def create(
        cls,
        *,
        last_name: str,
        first_name: str,
        middle_name: str | None = None,
        now: datetime | None = None,
    ) -> "ContactEntity":
        created_at = now or _now_utc()
        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )

    def update(
        self,
        *,
        last_name: str,
        first_name: str,
        middle_name: str | None,
        now: datetime | None = None,
    ) -> "ContactEntity":
        return replace(
            self,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            updated_at=now or _now_utc(),
        )


@dataclass(frozen=True, slots=True)
class CompanyEntity:
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    company_name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "last_name", normalize_company_last_name(self.last_name))
        object.__setattr__(
            self,
            "company_name",
            normalize_company_name(self.company_name),
        )

    @classmethod
    def create(
        cls,
        *,
        last_name: str,
        company_name: str,
        now: datetime | None = None,
    ) -> "CompanyEntity":
        created_at = now or _now_utc()
        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            last_name=last_name,
            company_name=company_name,
        )

    def update(
        self,
        *,
        last_name: str,
        company_name: str,
        now: datetime | None = None,
    ) -> "CompanyEntity":
        return replace(
            self,
            last_name=last_name,
            company_name=company_name,
            updated_at=now or _now_utc(),
        )


__all__ = [
    "CompanyEntity",
    "ContactEntity",
]
