from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.company.value_object.legal_name import CompanyLegalNameVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class CompanyEntity:
    """Самостоятельная компания с юридическим названием и аудитом."""

    id: CompanyIdVO
    legal_name: CompanyLegalNameVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        company_id: CompanyIdVO,
        legal_name: str,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        return cls(
            id=company_id,
            legal_name=CompanyLegalNameVO(legal_name),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    def update(self, *, legal_name: str, actor_id: EntityIdVO, now: datetime) -> bool:
        """Меняет название и аудит только при фактическом изменении."""
        name = CompanyLegalNameVO(legal_name)
        if name == self.legal_name:
            return False
        self.legal_name = name
        self.updated_at = now
        self.updated_by = actor_id
        return True
