from dataclasses import dataclass
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class SkuCodeVO:
    """Код карточки с точным регистрозависимым сравнением после trim."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует пробелы и проверяет длину SKU-кода."""
        value = self.value.strip()
        if not value or len(value) > 128 or any(ord(c) < 32 for c in value):
            raise InvalidCatalogValueError("Некорректный SKU-код.")
        object.__setattr__(self, "value", value)
