import re
from dataclasses import dataclass
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class CatalogCodeVO:
    """Стабильный код определения, независимый от перевода подписи."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет формат устойчивого кода без неявного переименования."""
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.value):
            raise InvalidCatalogValueError(
                "Код: латинская буква, затем a-z, 0-9 или _, до 64 символов."
            )
