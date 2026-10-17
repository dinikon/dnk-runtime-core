from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.identity.domain.user.aggregate import User
from src.modules.identity.domain.user.entity import UserEmail
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.identity.domain.user.value_object.user_email_id import UserEmailIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO


class UserMapper:
    """Преобразует строки хранения и агрегат пользователя без правил профиля и I/O."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any],
        email_rows: Sequence[Mapping[str, Any]],
        tenant_id: EntityIdVO,
    ) -> User:
        """Восстанавливает пользователя и emails через явные доменные фабрики."""
        return User.restore(
            id=UserIdVO.from_value(row["id"]),
            tenant_id=tenant_id,
            status=row["status"],
            role=row["role"],
            session_epoch=row["session_epoch"],
            last_name=row["last_name"],
            first_name=row["first_name"],
            middle_name=row["middle_name"],
            avatar=row["avatar"],
            interface_language=row["interface_language"],
            interface_theme=row["interface_theme"],
            timezone=row["timezone"],
            last_login_at=row["last_login_at"],
            last_active_at=row["last_active_at"],
            last_login_ip=row["last_login_ip"],
            initialized_at=row["initialized_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            display_currency=(
                CurrencyVO.from_value(row["display_currency"])
                if row["display_currency"] is not None
                else None
            ),
            emails=[
                UserEmail.restore(
                    id=UserEmailIdVO.from_value(email["id"]),
                    user_id=UserIdVO.from_value(email["user_id"]),
                    email=email["email"],
                    is_primary=email["is_primary"],
                    is_verified=email["is_verified"],
                    is_deleted=email["is_deleted"],
                    created_at=email["created_at"],
                    updated_at=email["updated_at"],
                )
                for email in email_rows
            ],
        )

    @staticmethod
    def to_insert_values(user: User) -> dict[str, Any]:
        """Извлекает колонки пользователя; default last_login_at остаётся в SQL."""
        return dict(
            id=user.id.uuid,
            status=user.status,
            role=user.role,
            session_epoch=user.session_epoch,
            user_type="user",
            last_name=user.last_name,
            first_name=user.first_name,
            middle_name=user.middle_name,
            avatar=user.avatar,
            interface_language=user.interface_language,
            interface_theme=user.interface_theme,
            timezone=user.timezone,
            display_currency=(
                None if user.display_currency is None else user.display_currency.value
            ),
            last_active_at=user.last_active_at,
            last_login_ip=user.last_login_ip,
            initialized_at=user.initialized_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            **(
                {"last_login_at": user.last_login_at}
                if user.last_login_at is not None
                else {}
            ),
        )

    @staticmethod
    def to_email_insert_values(email: UserEmail) -> dict[str, Any]:
        """Извлекает колонки внутреннего email без управления его состоянием."""
        return dict(
            id=email.id.uuid,
            user_id=email.user_id.uuid,
            email=email.email,
            is_primary=email.is_primary,
            is_verified=email.is_verified,
            is_deleted=email.is_deleted,
            created_at=email.created_at,
            updated_at=email.updated_at,
        )

    @staticmethod
    def to_profile_update_values(user: User) -> dict[str, Any]:
        """Извлекает изменённый профиль для UPDATE в текущей транзакции."""
        return dict(
            last_name=user.last_name,
            first_name=user.first_name,
            middle_name=user.middle_name,
            interface_language=user.interface_language,
            interface_theme=user.interface_theme,
            timezone=user.timezone,
            display_currency=(
                None if user.display_currency is None else user.display_currency.value
            ),
            updated_at=user.updated_at,
        )
