from __future__ import annotations

from src.modules.contact_point.domain.contact_point import ContactPointValidationError


class ContactPointSelectionError(ContactPointValidationError):
    pass


class UnsupportedContactPointChannelError(ContactPointSelectionError):
    def __init__(self, channel_code: str) -> None:
        super().__init__(
            f"Unsupported contact point selection channel: {channel_code}."
        )


class ContactPointSelectionNotFoundError(ContactPointSelectionError):
    def __init__(
        self,
        *,
        owner_object_id: str,
        owner_record_id: str,
        contact_point_type: str,
        strategy: str,
    ) -> None:
        super().__init__(
            "Contact point was not found for owner "
            f"{owner_record_id} in object {owner_object_id}, "
            f"type {contact_point_type}, strategy {strategy}."
        )


class ExplicitContactPointRequiredError(ContactPointSelectionError):
    def __init__(self) -> None:
        super().__init__(
            "explicit_contact_point_id is required for explicit contact point strategy."
        )


class ExplicitContactPointNotAttachedError(ContactPointSelectionError):
    def __init__(self, contact_point_id: str) -> None:
        super().__init__(
            f"Contact point {contact_point_id} is not actively attached to owner."
        )


class ExplicitContactPointTypeMismatchError(ContactPointSelectionError):
    def __init__(
        self,
        *,
        contact_point_id: str,
        expected_type: str,
        actual_type: str,
    ) -> None:
        super().__init__(
            f"Contact point {contact_point_id} has type {actual_type}, "
            f"expected {expected_type} for selected channel."
        )


class UnsupportedContactPointSelectionStrategyError(ContactPointSelectionError):
    def __init__(self, strategy: str) -> None:
        super().__init__(f"Unsupported contact point selection strategy: {strategy}.")


__all__ = [
    "ContactPointSelectionError",
    "ContactPointSelectionNotFoundError",
    "ExplicitContactPointNotAttachedError",
    "ExplicitContactPointRequiredError",
    "ExplicitContactPointTypeMismatchError",
    "UnsupportedContactPointChannelError",
    "UnsupportedContactPointSelectionStrategyError",
]
