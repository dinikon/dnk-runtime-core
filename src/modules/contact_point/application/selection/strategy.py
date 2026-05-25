from enum import StrEnum


class ContactPointSelectionStrategy(StrEnum):
    PRIMARY = "primary"
    LAST_ACTIVE = "last_active"
    ALL_ACTIVE = "all_active"
    EXPLICIT_CONTACT_POINT = "explicit_contact_point"


__all__ = ["ContactPointSelectionStrategy"]
