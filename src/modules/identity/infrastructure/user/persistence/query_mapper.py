from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.identity.application.user.query.get_current_user.record_dto import (
    GetCurrentUserRecordDTO,
)
from src.modules.identity.application.user.query.get_current_user.email_dto import (
    GetCurrentUserEmailDTO,
)


class UserProfileQueryMapper:
    """Преобразует строки проекции профиля в DTO конкретного сценария чтения."""

    @staticmethod
    def to_current_user(rows: Sequence[Mapping[str, Any]]) -> GetCurrentUserRecordDTO:
        """Собирает сохранённые поля профиля и emails без доменных фабрик и правил."""
        row = rows[0]
        return GetCurrentUserRecordDTO(
            id=row["id"],
            status=row["status"],
            role=row["role"],
            last_name=row["last_name"],
            first_name=row["first_name"],
            middle_name=row["middle_name"],
            avatar=row["avatar"],
            interface_language=row["interface_language"],
            interface_theme=row["interface_theme"],
            timezone=row["timezone"],
            display_currency=row["display_currency"],
            emails=[
                GetCurrentUserEmailDTO(
                    id=item["email_id"],
                    email=item["email"],
                    is_primary=item["is_primary"],
                    is_verified=item["is_verified"],
                )
                for item in rows
                if item["email_id"] is not None
            ],
        )
