from src.modules.shared.domain.errors import DomainError


class ContactNotFoundError(DomainError):
    """Доменная ошибка отсутствующего CRM-контакта."""

    def __init__(self, contact_id: str):
        """Формирует сообщение с id отсутствующего контакта."""
        super().__init__(f"Contact {contact_id} not found")


class InvalidContactNameError(DomainError):
    """Доменная ошибка некорректного имени контакта."""

    def __init__(self):
        """Формирует сообщение об обязательном first_name."""
        super().__init__("Contact first name must not be null.")


__all__ = [
    "ContactNotFoundError",
    "InvalidContactNameError",
]
