from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
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
    value: str | int | bool | PriceAmountVO | None

    def __post_init__(self) -> None:
        """Требует ID поля, текст, сумму без валюты либо явное пустое значение."""
        if not isinstance(self.field_id, FieldIdVO) or (
            self.value is not None
            and not isinstance(self.value, (str, int, bool, PriceAmountVO))
        ):
            raise InvalidPublicationValueError("Некорректное ручное значение поля.")
