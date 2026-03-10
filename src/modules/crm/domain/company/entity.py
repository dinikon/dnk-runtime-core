from dataclasses import dataclass, field
from typing import Self

from src.modules.crm.domain.company.value_objects import CompanyIdVO, CompanyNameVO
from src.modules.crm.domain.contact_point.contact_point_entity import (
    ContactPointEntity,
)
from src.modules.crm.domain.contact_point.contact_point_type_dictionary_entity import (
    ContactPointTypeDictionaryEntity,
)
from src.modules.crm.domain.contact_point.value_objects import (
    ContactPointIdVO,
    ContactPointKindVO,
    ContactPointTypeCodeVO,
)
from src.modules.crm.domain.error import ContactPointNotFoundError


@dataclass(slots=True)
class CompanyEntity:
    id: CompanyIdVO
    name: CompanyNameVO
    contact_points: list[ContactPointEntity] = field(default_factory=list)

    @classmethod
    def create(cls, *, company_name: str) -> Self:
        return cls(
            id=CompanyIdVO.new(),
            name=CompanyNameVO(company_name),
            contact_points=[],
        )

    @property
    def company_name(self) -> str:
        return self.name.value

    def rename(self, *, company_name: str) -> None:
        self.name = CompanyNameVO(company_name)

    def add_contact_point(
        self,
        *,
        kind: ContactPointKindVO,
        value: str,
        type_code: ContactPointTypeCodeVO,
        type_dictionary: ContactPointTypeDictionaryEntity | None = None,
        is_primary: bool = False,
        is_verified: bool = False,
        sort_order: int = 0,
    ) -> ContactPointEntity:
        if type_dictionary is not None:
            type_dictionary.ensure_active_type(kind=kind, code=type_code)

        point = ContactPointEntity.create(
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

    def remove_contact_point(self, point_id: ContactPointIdVO) -> None:
        self.contact_points = [
            point for point in self.contact_points if point.id != point_id
        ]

    def mark_contact_point_as_primary(self, point_id: ContactPointIdVO) -> None:
        target = self.get_contact_point(point_id)
        self._reset_primary_for_kind(kind=target.kind)
        target.mark_as_primary()

    def change_contact_point_value(self, point_id: ContactPointIdVO, value: str) -> None:
        target = self.get_contact_point(point_id)
        target.change_value(value)

    def change_contact_point_type(
        self,
        *,
        point_id: ContactPointIdVO,
        type_code: ContactPointTypeCodeVO,
        type_dictionary: ContactPointTypeDictionaryEntity | None = None,
    ) -> None:
        target = self.get_contact_point(point_id)
        if type_dictionary is not None:
            type_dictionary.ensure_active_type(kind=target.kind, code=type_code)
        target.change_type(type_code)

    def deactivate_contact_point(self, point_id: ContactPointIdVO) -> None:
        target = self.get_contact_point(point_id)
        target.deactivate()

    def activate_contact_point(self, point_id: ContactPointIdVO) -> None:
        target = self.get_contact_point(point_id)
        target.activate()

    def get_contact_point(self, point_id: ContactPointIdVO) -> ContactPointEntity:
        for point in self.contact_points:
            if point.id == point_id:
                return point
        raise ContactPointNotFoundError(str(point_id))

    def get_points_by_kind(self, kind: ContactPointKindVO) -> list[ContactPointEntity]:
        return [point for point in self.contact_points if point.kind == kind]

    def phones(self) -> list[ContactPointEntity]:
        return self.get_points_by_kind(ContactPointKindVO.phone())

    def emails(self) -> list[ContactPointEntity]:
        return self.get_points_by_kind(ContactPointKindVO.email())

    def sites(self) -> list[ContactPointEntity]:
        return self.get_points_by_kind(ContactPointKindVO.site())

    def websites(self) -> list[ContactPointEntity]:
        # Backward compatibility alias.
        return self.sites()

    def messengers(self) -> list[ContactPointEntity]:
        return self.get_points_by_kind(ContactPointKindVO.messenger())

    def _reset_primary_for_kind(self, *, kind: ContactPointKindVO) -> None:
        for point in self.contact_points:
            if point.kind == kind:
                point.unmark_as_primary()
