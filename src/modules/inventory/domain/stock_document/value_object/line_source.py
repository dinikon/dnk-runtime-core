from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_document.error import (
    InvalidDocumentLineSourceError,
)


@dataclass(frozen=True, slots=True)
class DocumentLineSourceVO:
    """Сохраняет систему и ссылку основания строки без владения чужой Entity."""

    system: str
    reference: str

    def __post_init__(self) -> None:
        """Требует непустые строки без управляющих символов, сохраняя регистр и ведущие нули."""
        for name in ("system", "reference"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or any(category(char) in ("Cc", "Cf") for char in value)
            ):
                raise InvalidDocumentLineSourceError(
                    "Нужны система и ссылка основания строки без управляющих символов."
                )
            object.__setattr__(self, name, value.strip())
