from src.modules.shared.domain.errors import DomainError


class ContactPointNotFoundError(DomainError):
    def __init__(self, contact_point_id: str) -> None:
        super().__init__(f"Contact point {contact_point_id} not found.")


class ContactPointValidationError(DomainError):
    pass


class InvalidContactPointValueError(ContactPointValidationError):
    def __init__(self, contact_point_type: str, value: str) -> None:
        super().__init__(
            f"Invalid {contact_point_type.lower()} contact point value: {value}."
        )


class UnsupportedContactPointTypeError(ContactPointValidationError):
    def __init__(self, contact_point_type: str) -> None:
        super().__init__(f"Unsupported contact point type: {contact_point_type}.")


__all__ = [
    "ContactPointNotFoundError",
    "ContactPointValidationError",
    "InvalidContactPointValueError",
    "UnsupportedContactPointTypeError",
]
