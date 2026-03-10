from dataclasses import dataclass

from modules.crm.domain.contact_point.value_objects import (
    ContactPointId,
    ContactPointKind,
    ContactPointTypeCode,
)


@dataclass(slots=True)
class ContactPoint:
    id: ContactPointId
    kind: ContactPointKind
    value: str
    type_code: ContactPointTypeCode
    is_primary: bool = False
    is_verified: bool = False
    sort_order: int = 0
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        kind: ContactPointKind,
        value: str,
        type_code: ContactPointTypeCode,
        is_primary: bool = False,
        is_verified: bool = False,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> "ContactPoint":
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Contact point value cannot be empty")

        return cls(
            id=ContactPointId.new(),
            kind=kind,
            value=normalized_value,
            type_code=type_code,
            is_primary=is_primary,
            is_verified=is_verified,
            sort_order=sort_order,
            is_active=is_active,
        )

    def change_value(self, new_value: str) -> None:
        normalized_value = new_value.strip()
        if not normalized_value:
            raise ValueError("Contact point value cannot be empty")
        self.value = normalized_value

    def change_type(self, new_type_code: ContactPointTypeCode) -> None:
        self.type_code = new_type_code

    def mark_as_primary(self) -> None:
        self.is_primary = True

    def unmark_as_primary(self) -> None:
        self.is_primary = False

    def verify(self) -> None:
        self.is_verified = True

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
