from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.domain.common.errors import ValidationError


@dataclass(slots=True)
class UserEmail:
    id: UUID
    user_id: UUID
    email: str
    is_primary: bool
    is_verified: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class User:
    id: UUID
    tenant_id: UUID
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str | None
    timezone: str
    last_login_at: datetime | None
    last_active_at: datetime
    last_login_ip: str | None
    initialized_at: datetime | None
    created_at: datetime
    updated_at: datetime
    emails: list[UserEmail] = field(default_factory=list)

    @classmethod
    def create_tenant_admin(
        cls,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
    ) -> "User":
        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        if not normalized_first_name:
            raise ValidationError("User first name must not be empty.")
        if not normalized_last_name:
            raise ValidationError("User last name must not be empty.")

        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            tenant_id=tenant_id,
            status="active",
            last_name=normalized_last_name,
            first_name=normalized_first_name,
            middle_name=None,
            avatar=None,
            interface_language="uk",
            interface_theme="system",
            timezone="Europe/Kyiv",
            last_login_at=None,
            last_active_at=now,
            last_login_ip=None,
            initialized_at=None,
            created_at=now,
            updated_at=now,
        )

    def add_email(
        self,
        email: str,
        *,
        is_primary: bool = False,
        is_verified: bool = False,
    ) -> UserEmail:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValidationError("User email must not be empty.")

        if is_primary and any(existing.is_primary for existing in self.emails):
            raise ValidationError("User already has a primary email.")

        now = datetime.now(UTC)
        user_email = UserEmail(
            id=uuid6.uuid7(),
            user_id=self.id,
            email=normalized_email,
            is_primary=is_primary,
            is_verified=is_verified,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        self.emails.append(user_email)
        self.updated_at = now
        return user_email
