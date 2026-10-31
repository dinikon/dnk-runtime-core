"""Текущее поколение проверки подключения."""

from dataclasses import dataclass
from datetime import datetime

from src.modules.channels.domain.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.error import InvalidChannelStateError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationVO:
    """Хранит согласованный результат или ожидающее поколение проверки."""

    job_id: EntityIdVO
    config_revision: int
    status: VerificationStatus = VerificationStatus.PENDING
    checked_at: datetime | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Отклоняет несовместимые статус, время результата и причину отказа."""
        if (
            not isinstance(self.job_id, EntityIdVO)
            or type(self.config_revision) is not int
            or self.config_revision < 1
            or not isinstance(self.status, VerificationStatus)
        ):
            raise InvalidChannelStateError("Некорректное поколение проверки.")
        if self.status is VerificationStatus.PENDING:
            if self.checked_at is not None or self.error_code is not None:
                raise InvalidChannelStateError(
                    "Ожидающая проверка не имеет результата."
                )
        elif not isinstance(self.checked_at, datetime):
            raise InvalidChannelStateError(
                "Завершённая проверка требует времени результата."
            )
        if self.status is VerificationStatus.VERIFIED and self.error_code is not None:
            raise InvalidChannelStateError("Успешная проверка не имеет ошибки.")
        if self.status is VerificationStatus.ERROR and (
            not isinstance(self.error_code, str) or not self.error_code.strip()
        ):
            raise InvalidChannelStateError("Отказ проверки требует причину.")
