from dataclasses import dataclass

from src.modules.crm.domain.contact.error import InvalidContactNameError


@dataclass(frozen=True, slots=True)
class ContactNameVO:
    """Полное имя физического лица с нормализованными краями строк."""

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None

    def __post_init__(self) -> None:
        """Проверяет части имени и сохраняет их нормализованные значения."""
        for field in ("first_name", "last_name", "middle_name"):
            value = getattr(self, field)
            if field != "first_name" and value is None:
                continue
            if not isinstance(value, str):
                raise InvalidContactNameError(f"{field}: ожидается строка.")
            value = value.strip()
            if field != "first_name" and not value:
                object.__setattr__(self, field, None)
                continue
            if not 1 <= len(value) <= 255:
                raise InvalidContactNameError(
                    f"{field}: требуется от 1 до 255 символов."
                )
            object.__setattr__(self, field, value)
