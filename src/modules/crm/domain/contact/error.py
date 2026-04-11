from src.modules.shared.domain.errors import DomainError


class ContactNotFoundError(DomainError):
    def __init__(self, contact_id: str):
        super().__init__(f"Contact {contact_id} not found")


class InvalidContactNameError(DomainError):
    def __init__(self):
        super().__init__("Contact first name must not be null.")


__all__ = [
    "ContactNotFoundError",
    "InvalidContactNameError",
]
