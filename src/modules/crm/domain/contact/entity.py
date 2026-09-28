from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import datetime

from src.modules.crm.domain.contact.value_object import ContactIdVO, ContactNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.domain.links import company_selection, ensure_current_links


@dataclass(slots=True)
class Contact:
    """Физическое лицо в CRM."""

    id: ContactIdVO
    name: ContactNameVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    _company_ids: frozenset[CompanyIdVO] = field(default_factory=frozenset, repr=False)

    def __post_init__(self) -> None:
        if type(self.id) is not ContactIdVO:
            raise EntityIdTypeError("Contact id must use ContactIdVO.")
        if not isinstance(self.created_by, EntityIdVO) or not isinstance(
            self.updated_by, EntityIdVO
        ):
            raise EntityIdTypeError("Contact audit ids must use EntityIdVO.")
        if not isinstance(self.name, ContactNameVO):
            raise TypeError("Contact name must use ContactNameVO.")
        self._company_ids = company_selection(self._company_ids)

    @property
    def company_ids(self) -> frozenset[CompanyIdVO]:
        return self._company_ids

    def replace_companies(
        self,
        *,
        requested: Collection[CompanyIdVO],
        expected: Collection[CompanyIdVO] | None,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> bool:
        desired = company_selection(requested)
        if expected is not None:
            company_selection(expected)
        ensure_current_links(self.company_ids, expected)
        if desired == self.company_ids:
            return False
        self._company_ids = desired
        self.updated_at, self.updated_by = now, actor_id
        return True

    def link_company(
        self, company_id: CompanyIdVO, *, actor_id: EntityIdVO, now: datetime
    ) -> bool:
        company_selection((company_id,))
        return self.replace_companies(
            requested=self.company_ids | {company_id},
            expected=self.company_ids,
            actor_id=actor_id,
            now=now,
        )

    def unlink_company(
        self, company_id: CompanyIdVO, *, actor_id: EntityIdVO, now: datetime
    ) -> bool:
        company_selection((company_id,))
        return self.replace_companies(
            requested=self.company_ids - {company_id},
            expected=self.company_ids,
            actor_id=actor_id,
            now=now,
        )

    @classmethod
    def create(
        cls,
        *,
        contact_id: ContactIdVO,
        actor_id: EntityIdVO,
        now: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> "Contact":
        """Создаёт контакт с едиными audit-значениями."""
        return cls(
            id=contact_id,
            name=ContactNameVO(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
            ),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    def update(
        self,
        *,
        actor_id: EntityIdVO,
        now: datetime,
        first_name: str,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> bool:
        """Меняет ФИО и audit только при фактическом изменении."""
        name = ContactNameVO(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )
        if name == self.name:
            return False
        self.name = name
        self.updated_at = now
        self.updated_by = actor_id
        return True


__all__ = ["Contact"]
