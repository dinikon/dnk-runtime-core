from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.company.value_object import CompanyIdVO, CompanyNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class Company:
    """Компания в CRM."""

    id: CompanyIdVO
    name: CompanyNameVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def __post_init__(self) -> None:
        if type(self.id) is not CompanyIdVO:
            raise EntityIdTypeError("Company id must use CompanyIdVO.")
        if not isinstance(self.created_by, EntityIdVO) or not isinstance(
            self.updated_by, EntityIdVO
        ):
            raise EntityIdTypeError("Company audit ids must use EntityIdVO.")
        if not isinstance(self.name, CompanyNameVO):
            raise TypeError("Company name must use CompanyNameVO.")

    @classmethod
    def create(
        cls,
        *,
        company_id: CompanyIdVO,
        actor_id: EntityIdVO,
        now: datetime,
        name: str,
    ) -> "Company":
        """Создаёт компанию с едиными audit-значениями."""
        return cls(
            id=company_id,
            name=CompanyNameVO(name),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    def update(self, *, actor_id: EntityIdVO, now: datetime, name: str) -> bool:
        """Меняет название и audit только при фактическом изменении."""
        company_name = CompanyNameVO(name)
        if company_name == self.name:
            return False
        self.name = company_name
        self.updated_at = now
        self.updated_by = actor_id
        return True


__all__ = ["Company"]
