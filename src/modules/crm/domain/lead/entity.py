from dataclasses import dataclass, field
from typing import Self

from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.contact.entity import ContactEntity
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
from src.modules.crm.domain.deal.entity import DealEntity
from src.modules.crm.domain.error import (
    ContactPointNotFoundError,
    LeadCompanyNameRequiredForConversionError,
    LeadPersonNameRequiredForConversionError,
)
from src.modules.crm.domain.lead.conversion.mode import LeadConversionModeVO
from src.modules.crm.domain.lead.conversion.result import LeadConversionResultVO
from src.modules.crm.domain.lead.value_objects import LeadIdVO, LeadTitleVO
from src.modules.crm.domain.shared.company_name import CompanyNameVO
from src.modules.crm.domain.shared.person_name import PersonNameVO


@dataclass(slots=True)
class LeadEntity:
    id: LeadIdVO
    title: LeadTitleVO
    person_name: PersonNameVO | None = None
    company_name: CompanyNameVO | None = None
    contact_points: list[ContactPointEntity] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        person_name: PersonNameVO | None = None,
        company_name: str | CompanyNameVO | None = None,
    ) -> Self:
        normalized_company_name: CompanyNameVO | None = None
        if isinstance(company_name, str):
            normalized_company_name = CompanyNameVO(company_name)
        elif company_name is not None:
            normalized_company_name = company_name

        return cls(
            id=LeadIdVO.new(),
            title=LeadTitleVO(title),
            person_name=person_name,
            company_name=normalized_company_name,
            contact_points=[],
        )

    def rename(self, *, title: str) -> None:
        self.title = LeadTitleVO(title)

    def set_person_name(
        self,
        *,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> None:
        self.person_name = PersonNameVO(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )

    def clear_person_name(self) -> None:
        self.person_name = None

    def set_company_name(self, value: str) -> None:
        self.company_name = CompanyNameVO(value)

    def clear_company_name(self) -> None:
        self.company_name = None

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

    def convert(
        self,
        *,
        mode: LeadConversionModeVO,
        type_dictionary: ContactPointTypeDictionaryEntity | None = None,
    ) -> LeadConversionResultVO:
        contact: ContactEntity | None = None
        company: CompanyEntity | None = None
        deal: DealEntity | None = None

        include_contact = mode in (
            LeadConversionModeVO.CONTACT_ONLY,
            LeadConversionModeVO.CONTACT_AND_COMPANY,
            LeadConversionModeVO.DEAL_AND_CONTACT,
            LeadConversionModeVO.DEAL_AND_CONTACT_AND_COMPANY,
        )
        include_company = mode in (
            LeadConversionModeVO.COMPANY_ONLY,
            LeadConversionModeVO.CONTACT_AND_COMPANY,
            LeadConversionModeVO.DEAL_AND_COMPANY,
            LeadConversionModeVO.DEAL_AND_CONTACT_AND_COMPANY,
        )
        include_deal = mode in (
            LeadConversionModeVO.DEAL_ONLY,
            LeadConversionModeVO.DEAL_AND_CONTACT,
            LeadConversionModeVO.DEAL_AND_COMPANY,
            LeadConversionModeVO.DEAL_AND_CONTACT_AND_COMPANY,
        )

        if include_contact:
            person_name = self._require_person_name_for_contact_conversion()
            contact = ContactEntity.create(
                first_name=person_name.first_name,
                last_name=person_name.last_name,
                middle_name=person_name.middle_name,
            )
            self._copy_contact_points_to_contact(
                contact=contact,
                type_dictionary=type_dictionary,
            )

        if include_company:
            company_name = self._require_company_name_for_company_conversion()
            company = CompanyEntity.create(company_name=company_name.value)
            self._copy_contact_points_to_company(
                company=company,
                type_dictionary=type_dictionary,
            )

        if include_deal:
            deal = DealEntity.create(title=self.title.value)

        return LeadConversionResultVO(contact=contact, company=company, deal=deal)

    def _require_person_name_for_contact_conversion(self) -> PersonNameVO:
        if self.person_name is None:
            raise LeadPersonNameRequiredForConversionError()
        return self.person_name

    def _require_company_name_for_company_conversion(self) -> CompanyNameVO:
        if self.company_name is None:
            raise LeadCompanyNameRequiredForConversionError()
        return self.company_name

    def _copy_contact_points_to_contact(
        self,
        *,
        contact: ContactEntity,
        type_dictionary: ContactPointTypeDictionaryEntity | None = None,
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
        company: CompanyEntity,
        type_dictionary: ContactPointTypeDictionaryEntity | None = None,
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


__all__ = ["LeadEntity"]
