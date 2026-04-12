from dataclasses import dataclass

from src.modules.crm.domain.contact.error import InvalidContactNameError


@dataclass(slots=True, frozen=True)
class ContactNameVO:
    """Value object ФИО CRM-контакта."""

    last_name: str | None
    first_name: str
    middle_name: str | None

    def __post_init__(self) -> None:
        """Проверяет обязательность first_name."""
        if self.first_name is None:
            raise InvalidContactNameError()
