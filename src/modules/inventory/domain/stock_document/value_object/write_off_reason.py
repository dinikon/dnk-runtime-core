from dataclasses import dataclass
from src.modules.inventory.domain.stock_document.write_off_error import (
    InvalidWriteOffReasonError,
)


@dataclass(frozen=True, slots=True)
class WriteOffReasonVO:
    """Хранит текстовую причину без внешних пробелов и потери регистра или внутренних переносов."""

    value: str

    def __post_init__(self) -> None:
        """Требует непустой текст до 1000 символов без недопустимых управляющих символов."""
        if not isinstance(self.value, str):
            raise InvalidWriteOffReasonError("Укажите текстовую причину списания.")
        value = self.value.strip()
        if (
            not value
            or len(value) > 1000
            or any(ord(c) < 32 and c not in "\n\r\t" for c in value)
            or "\x7f" in value
        ):
            raise InvalidWriteOffReasonError(
                "Причина списания должна содержать от 1 до 1000 символов без служебных знаков."
            )
        object.__setattr__(self, "value", value)
