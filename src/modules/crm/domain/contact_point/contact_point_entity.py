from dataclasses import dataclass

from src.modules.crm.domain.error import ContactPointValueRequiredError
from src.modules.crm.domain.contact_point.value_objects import (
    ContactPointIdVO,
    ContactPointKindVO,
    ContactPointTypeCodeVO,
)


@dataclass(slots=True)
class ContactPointEntity:
    id: ContactPointIdVO
    kind: ContactPointKindVO
    value: str
    type_code: ContactPointTypeCodeVO
    is_primary: bool = False
    is_verified: bool = False
    sort_order: int = 0
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        kind: ContactPointKindVO,
        value: str,
        type_code: ContactPointTypeCodeVO,
        is_primary: bool = False,
        is_verified: bool = False,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> "ContactPointEntity":
        normalized_value = value.strip()
        if not normalized_value:
            raise ContactPointValueRequiredError()

        return cls(
            id=ContactPointIdVO.new(),
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
            raise ContactPointValueRequiredError()
        self.value = normalized_value

    def change_type(self, new_type_code: ContactPointTypeCodeVO) -> None:
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


__all__ = ["ContactPointEntity"]

