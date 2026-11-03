from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_document.error import InvalidDocumentSourceError


@dataclass(frozen=True, slots=True)
class DocumentSourceVO:
    """Сохраняет внешнюю систему и ссылку основания без загрузки чужого агрегата."""

    system: str
    reference: str

    def __post_init__(self) -> None:
        """Требует непустые строки без управляющих символов, сохраняя регистр ссылки."""
        for name in ("system", "reference"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or any(category(char) in ("Cc", "Cf") for char in value)
            ):
                raise InvalidDocumentSourceError(
                    "Укажите систему и внешнюю ссылку без управляющих символов."
                )
            object.__setattr__(self, name, value.strip())
