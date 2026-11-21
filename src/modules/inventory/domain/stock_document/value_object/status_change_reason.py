from dataclasses import dataclass
from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStatusChangeReasonError,
)


@dataclass(frozen=True, slots=True)
class StatusChangeReasonVO:
    """Хранит текстовую причину без внешних пробелов и потери регистра или внутренних переносов."""

    value: str

    def __post_init__(self) -> None:
        """Требует непустой текст до 1000 символов без недопустимых управляющих символов."""
        if not isinstance(self.value, str):
            raise InvalidStatusChangeReasonError(
                "Укажите текстовую причину изменения состояния."
            )
        value = self.value.strip()
        if (
            not value
            or len(value) > 1000
            or any(ord(c) < 32 and c not in "\n\r\t" for c in value)
            or "\x7f" in value
        ):
            raise InvalidStatusChangeReasonError(
                "Причина изменения состояния должна содержать от 1 до 1000 символов без служебных знаков."
            )
        object.__setattr__(self, "value", value)
