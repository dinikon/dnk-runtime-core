from __future__ import annotations

from typing import Sequence
from uuid import UUID

from src.modules.identity.domain.user import User, UserEmail
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel


def map_user_model(
    user_model: UserModel, email_models: Sequence[UserEmailModel]
) -> User:
    """Мапит ORM user model и email models в доменную User entity."""
    return User(
        id=_to_uuid(user_model.id),
        tenant_id=_to_uuid(user_model.tenant_id),
        status=user_model.status,
        last_name=user_model.last_name,
        first_name=user_model.first_name,
        middle_name=user_model.middle_name,
        avatar=user_model.avatar,
        interface_language=user_model.interface_language,
        interface_theme=user_model.interface_theme,
        timezone=user_model.timezone,
        last_login_at=user_model.last_login_at,
        last_active_at=user_model.last_active_at,
        last_login_ip=user_model.last_login_ip,
        initialized_at=user_model.initialized_at,
        created_at=user_model.created_at,
        updated_at=user_model.updated_at,
        emails=[map_user_email_model(email_model) for email_model in email_models],
    )


def map_user_email_model(model: UserEmailModel) -> UserEmail:
    """Мапит ORM email model в доменную UserEmail entity."""
    return UserEmail(
        id=_to_uuid(model.id),
        user_id=_to_uuid(model.user_id),
        email=model.email,
        is_primary=model.is_primary,
        is_verified=model.is_verified,
        is_deleted=model.is_deleted,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_uuid(value: UUID | str) -> UUID:
    """Приводит UUID или строку из ORM к UUID."""
    if isinstance(value, UUID):
        return value
    return UUID(value)


__all__ = ["map_user_email_model", "map_user_model"]
