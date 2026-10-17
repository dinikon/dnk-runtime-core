from dataclasses import dataclass
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class CatalogLabelVO:
    """Содержательная локализованная подпись определения."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет длину и нормализует окружающие пробелы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or len(self.value) > 255
        ):
            raise InvalidCatalogValueError("Подпись: от 1 до 255 символов.")
        object.__setattr__(self, "value", self.value.strip())
