from dataclasses import dataclass, field
from typing import Self

from src.modules.crm.domain.contact.value_objects import ContactId, PersonName
from src.modules.crm.domain.contact_point.entity import (
    ContactPoint,
    ContactPointTypeDictionary,
)
from src.modules.crm.domain.contact_point.value_objects import (
    ContactPointId,
    ContactPointKind,
    ContactPointTypeCode,
)
from src.modules.crm.domain.error import ContactPointNotFoundError

@dataclass(slots=True)
class Contact:
    id: ContactId
    name: PersonName
    contact_points: list[ContactPoint] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> Self:
        return cls(
            id=ContactId.new(),
            name=PersonName(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
            ),
            contact_points=[],
        )

    @property
    def first_name(self) -> str:
        return self.name.first_name

    @property
    def last_name(self) -> str | None:
        return self.name.last_name

    @property
    def middle_name(self) -> str | None:
        return self.name.middle_name

    def rename(
        self,
        *,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> None:
        self.name = PersonName(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )

    def add_contact_point(
        self,
        *,
        kind: ContactPointKind,
        value: str,
        type_code: ContactPointTypeCode,
        type_dictionary: ContactPointTypeDictionary | None = None,
        is_primary: bool = False,
        is_verified: bool = False,
        sort_order: int = 0,
    ) -> ContactPoint:
        if type_dictionary is not None:
            type_dictionary.ensure_active_type(kind=kind, code=type_code)

        point = ContactPoint.create(
            kind=kind,
            value=value,
            type_code=type_code,
            is_primary=is_primary,
            is_verified=is_verified,
            sort_order=sort_order,
        )

        if is_primary:
            self._reset_primary_for_kind(kind=kind)

        self.contact_points.append(point)
        return point

    def remove_contact_point(self, point_id: ContactPointId) -> None:
        self.contact_points = [
            point for point in self.contact_points if point.id != point_id
        ]

    def mark_contact_point_as_primary(self, point_id: ContactPointId) -> None:
        target = self.get_contact_point(point_id)
        self._reset_primary_for_kind(kind=target.kind)
        target.mark_as_primary()

    def change_contact_point_value(self, point_id: ContactPointId, value: str) -> None:
        target = self.get_contact_point(point_id)
        target.change_value(value)

    def change_contact_point_type(
        self,
        *,
        point_id: ContactPointId,
        type_code: ContactPointTypeCode,
        type_dictionary: ContactPointTypeDictionary | None = None,
    ) -> None:
        target = self.get_contact_point(point_id)
        if type_dictionary is not None:
            type_dictionary.ensure_active_type(kind=target.kind, code=type_code)
        target.change_type(type_code)

    def deactivate_contact_point(self, point_id: ContactPointId) -> None:
        target = self.get_contact_point(point_id)
        target.deactivate()

    def activate_contact_point(self, point_id: ContactPointId) -> None:
        target = self.get_contact_point(point_id)
        target.activate()

    def get_contact_point(self, point_id: ContactPointId) -> ContactPoint:
        for point in self.contact_points:
            if point.id == point_id:
                return point
        raise ContactPointNotFoundError(str(point_id))

    def get_points_by_kind(self, kind: ContactPointKind) -> list[ContactPoint]:
        return [point for point in self.contact_points if point.kind == kind]

    def phones(self) -> list[ContactPoint]:
        return self.get_points_by_kind(ContactPointKind.phone())

    def emails(self) -> list[ContactPoint]:
        return self.get_points_by_kind(ContactPointKind.email())

    def sites(self) -> list[ContactPoint]:
        return self.get_points_by_kind(ContactPointKind.site())

    def websites(self) -> list[ContactPoint]:
        # Backward compatibility alias.
        return self.sites()

    def messengers(self) -> list[ContactPoint]:
        return self.get_points_by_kind(ContactPointKind.messenger())

    def _reset_primary_for_kind(self, *, kind: ContactPointKind) -> None:
        for point in self.contact_points:
            if point.kind == kind:
                point.unmark_as_primary()
