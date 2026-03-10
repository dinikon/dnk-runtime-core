from dataclasses import dataclass, field
from enum import StrEnum
from typing import Self

from src.modules.crm.domain.company.entity import Company
from src.modules.crm.domain.contact_point.entity import (
    ContactPoint,
    ContactPointTypeDictionary,
)
from src.modules.crm.domain.contact_point.value_objects import (
    ContactPointId,
    ContactPointKind,
    ContactPointTypeCode,
)
from src.modules.crm.domain.contact.entity import Contact
from src.modules.crm.domain.error import (
    ContactPointNotFoundError,
    LeadCompanyNameRequiredForConversionError,
    LeadPersonNameRequiredForConversionError,
)
from src.modules.crm.domain.lead.value_objects import LeadId, LeadTitle
from src.modules.crm.domain.shared.company_name import CompanyName
from src.modules.crm.domain.shared.person_name import PersonName


class LeadConversionMode(StrEnum):
    CONTACT_ONLY = "contact_only"
    COMPANY_ONLY = "company_only"
    CONTACT_AND_COMPANY = "contact_and_company"


@dataclass(frozen=True, slots=True)
class LeadConversionResult:
    contact: Contact | None
    company: Company | None


@dataclass(slots=True)
class Lead:
    id: LeadId
    title: LeadTitle
    person_name: PersonName | None = None
    company_name: CompanyName | None = None
    contact_points: list[ContactPoint] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        person_name: PersonName | None = None,
        company_name: str | CompanyName | None = None,
    ) -> Self:
        normalized_company_name: CompanyName | None = None
        if isinstance(company_name, str):
            normalized_company_name = CompanyName(company_name)
        elif company_name is not None:
            normalized_company_name = company_name

        return cls(
            id=LeadId.new(),
            title=LeadTitle(title),
            person_name=person_name,
            company_name=normalized_company_name,
            contact_points=[],
        )

    def rename(self, *, title: str) -> None:
        self.title = LeadTitle(title)

    def set_person_name(
        self,
        *,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> None:
        self.person_name = PersonName(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )

    def clear_person_name(self) -> None:
        self.person_name = None

    def set_company_name(self, value: str) -> None:
        self.company_name = CompanyName(value)

    def clear_company_name(self) -> None:
        self.company_name = None

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

    def convert(
        self,
        *,
        mode: LeadConversionMode,
        type_dictionary: ContactPointTypeDictionary | None = None,
    ) -> LeadConversionResult:
        contact: Contact | None = None
        company: Company | None = None

        if mode in (
            LeadConversionMode.CONTACT_ONLY,
            LeadConversionMode.CONTACT_AND_COMPANY,
        ):
            person_name = self._require_person_name_for_contact_conversion()
            contact = Contact.create(
                first_name=person_name.first_name,
                last_name=person_name.last_name,
                middle_name=person_name.middle_name,
            )
            self._copy_contact_points_to_contact(
                contact=contact,
                type_dictionary=type_dictionary,
            )

        if mode in (
            LeadConversionMode.COMPANY_ONLY,
            LeadConversionMode.CONTACT_AND_COMPANY,
        ):
            company_name = self._require_company_name_for_company_conversion()
            company = Company.create(company_name=company_name.value)
            self._copy_contact_points_to_company(
                company=company,
                type_dictionary=type_dictionary,
            )

        return LeadConversionResult(contact=contact, company=company)

    def _require_person_name_for_contact_conversion(self) -> PersonName:
        if self.person_name is None:
            raise LeadPersonNameRequiredForConversionError()
        return self.person_name

    def _require_company_name_for_company_conversion(self) -> CompanyName:
        if self.company_name is None:
            raise LeadCompanyNameRequiredForConversionError()
        return self.company_name

    def _copy_contact_points_to_contact(
        self,
        *,
        contact: Contact,
        type_dictionary: ContactPointTypeDictionary | None = None,
    ) -> None:
        for point in self.contact_points:
            created = contact.add_contact_point(
                kind=point.kind,
                value=point.value,
                type_code=point.type_code,
                type_dictionary=type_dictionary,
                is_primary=point.is_primary,
                is_verified=point.is_verified,
                sort_order=point.sort_order,
            )
            if not point.is_active:
                created.deactivate()

    def _copy_contact_points_to_company(
        self,
        *,
        company: Company,
        type_dictionary: ContactPointTypeDictionary | None = None,
    ) -> None:
        for point in self.contact_points:
            created = company.add_contact_point(
                kind=point.kind,
                value=point.value,
                type_code=point.type_code,
                type_dictionary=type_dictionary,
                is_primary=point.is_primary,
                is_verified=point.is_verified,
                sort_order=point.sort_order,
            )
            if not point.is_active:
                created.deactivate()
