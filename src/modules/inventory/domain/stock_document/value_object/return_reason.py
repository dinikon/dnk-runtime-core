from dataclasses import dataclass
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidReturnReasonError,
)


@dataclass(frozen=True, slots=True)
class ReturnReasonVO:
    """Хранит текстовую причину без внешних пробелов и потери регистра или внутренних переносов."""

    value: str

    def __post_init__(self) -> None:
        """Требует непустой текст до 1000 символов без недопустимых управляющих символов."""
        if not isinstance(self.value, str):
            raise InvalidReturnReasonError("Укажите текстовую причину возврата.")
        value = self.value.strip()
        if (
            not value
            or len(value) > 1000
            or any(ord(c) < 32 and c not in "\n\r\t" for c in value)
            or "\x7f" in value
        ):
            raise InvalidReturnReasonError(
                "Причина возврата должна содержать от 1 до 1000 символов без служебных знаков."
            )
        object.__setattr__(self, "value", value)
