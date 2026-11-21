from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_document.error import InvalidDocumentSourceError


@dataclass(frozen=True, slots=True)
class DocumentSourceVO:
    """Сохраняет внешнюю систему и ссылку основания без загрузки чужого агрегата."""

    system: str
    reference: str
    version: int | None = None

    def __post_init__(self) -> None:
        """Проверяет непустые строки без управляющих символов и необязательную строгую версию основания."""
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
        if self.version is not None and (
            type(self.version) is not int or self.version < 0
        ):
            raise InvalidDocumentSourceError(
                "Версия основания должна быть целой неотрицательной без bool или None."
            )
