import re
from dataclasses import dataclass
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class LocaleVO:
    """Явный BCP 47 код; активность проверяет Application через reference_data."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет форму кода, не выбирая язык или fallback."""
        if len(self.value) > 64 or not re.fullmatch(
            r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", self.value
        ):
            raise InvalidCatalogValueError("Некорректный код locale.")
