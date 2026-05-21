from src.modules.shared.domain.errors import DomainError


class ContactPointBindingNotFoundError(DomainError):
    def __init__(self, binding_id: str) -> None:
        super().__init__(f"Contact point binding {binding_id} not found.")


class ContactPointOwnerNotFoundError(DomainError):
    def __init__(self, owner_object_id: str, owner_record_id: str) -> None:
        super().__init__(
            "Contact point owner record "
            f"{owner_record_id} was not found in object {owner_object_id}."
        )


__all__ = [
    "ContactPointBindingNotFoundError",
    "ContactPointOwnerNotFoundError",
]
