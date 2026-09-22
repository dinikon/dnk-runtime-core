from typing import Protocol

from src.modules.crm.domain.company.entity import Company
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CompanyRepositoryProtocol(Protocol):
    """Порт командного хранения компаний."""

    async def get(
        self,
        tenant_id: EntityIdVO,
        company_id: CompanyIdVO,
        *,
        for_update: bool = False,
    ) -> Company: ...

    async def add(self, tenant_id: EntityIdVO, company: Company) -> None: ...

    async def save(self, tenant_id: EntityIdVO, company: Company) -> None: ...

    async def delete(self, tenant_id: EntityIdVO, company_id: CompanyIdVO) -> None: ...


__all__ = ["CompanyRepositoryProtocol"]
