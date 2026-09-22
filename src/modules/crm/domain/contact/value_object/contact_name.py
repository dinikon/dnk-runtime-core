from dataclasses import dataclass

from src.modules.crm.domain.contact.error import InvalidContactNameError


def _required_name(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise InvalidContactNameError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidContactNameError(f"{label} must not be empty.")
    if len(normalized) > 255:
        raise InvalidContactNameError(f"{label} must not exceed 255 characters.")
    return normalized


def _optional_name(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidContactNameError(f"{label} must be a string or null.")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 255:
        raise InvalidContactNameError(f"{label} must not exceed 255 characters.")
    return normalized


@dataclass(slots=True, frozen=True)
class ContactNameVO:
    """Нормализованное ФИО контакта."""

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "first_name", _required_name(self.first_name, "First name")
        )
        object.__setattr__(
            self, "last_name", _optional_name(self.last_name, "Last name")
        )
        object.__setattr__(
            self, "middle_name", _optional_name(self.middle_name, "Middle name")
        )

    @property
    def display_name(self) -> str:
        """Возвращает ФИО в порядке фамилия, имя, отчество."""
        return " ".join(
            part for part in (self.last_name, self.first_name, self.middle_name) if part
        )


__all__ = ["ContactNameVO"]
