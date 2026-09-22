from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.company.entity import Company
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class CompanyDTO:
    """Публичные данные CRM-компании."""

    id: CompanyIdVO
    name: str
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO


@dataclass(slots=True, frozen=True)
class CompanyPageDTO:
    """Страница компаний с полным количеством результатов."""

    items: tuple[CompanyDTO, ...]
    total: int
    limit: int
    offset: int


def company_dto(company: Company) -> CompanyDTO:
    """Преобразует aggregate компании в application DTO."""
    return CompanyDTO(
        id=company.id,
        name=company.name.value,
        created_at=company.created_at,
        updated_at=company.updated_at,
        created_by=company.created_by,
        updated_by=company.updated_by,
    )


__all__ = ["CompanyDTO", "CompanyPageDTO", "company_dto"]
