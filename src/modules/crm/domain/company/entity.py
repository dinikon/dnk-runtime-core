from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.crm.domain.company.value_object import (
    CompanyIdVO,
    CompanyLegalNameVO,
)


@dataclass(slots=True)
class CompanyEntity:
    """Доменная сущность CRM-компании."""

    id: CompanyIdVO
    created_at: datetime
    updated_at: datetime
    legal_name: CompanyLegalNameVO

    @classmethod
    def create(
        cls,
        *,
        id_: CompanyIdVO,
        now: datetime,
        legal_name: str,
    ) -> Self:
        """Создает компанию с едиными created_at/updated_at."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            legal_name=CompanyLegalNameVO(legal_name),
        )

    def update(
        self,
        *,
        now: datetime,
        legal_name: str,
    ) -> None:
        """Обновляет юридическое название компании, если данные изменились."""
        new_legal_name = CompanyLegalNameVO(legal_name)

        if self.legal_name == new_legal_name:
            return

        self.legal_name = new_legal_name
        self.updated_at = now
