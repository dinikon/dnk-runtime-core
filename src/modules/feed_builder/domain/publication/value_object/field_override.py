from dataclasses import dataclass
from typing import ClassVar
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.publication.enum.override_mode import OverrideMode
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)


@dataclass(frozen=True, slots=True)
class FieldOverrideVO:
    """Хранит ручное значение поля; None отличается от отсутствия override."""

    mode: ClassVar[OverrideMode] = OverrideMode.MANUAL
    field_id: FieldIdVO
    value: str | MoneyVO | None

    def __post_init__(self) -> None:
        """Требует ID поля и текст, денежное значение либо явное пустое значение."""
        if not isinstance(self.field_id, FieldIdVO) or (
            self.value is not None and not isinstance(self.value, (str, MoneyVO))
        ):
            raise InvalidPublicationValueError("Некорректное ручное значение поля.")
