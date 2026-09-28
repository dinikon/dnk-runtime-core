from .list_available_companies_query import ListAvailableCompaniesQuery
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.dto import CompanyDetailsDTO
from typing import Protocol

from src.modules.crm.application.company.dto.company_dto import CompanyPageDTO
from src.modules.crm.application.company.query.list_companies_query import (
    ListCompaniesQuery,
)


class CompanyQueryRepositoryProtocol(Protocol):
    """Порт чтения страницы компаний."""

    async def list(self, query: ListCompaniesQuery) -> CompanyPageDTO: ...

    async def get_details(
        self, tenant_id: EntityIdVO, identifier: CompanyIdVO
    ) -> CompanyDetailsDTO | None: ...

    async def list_available(
        self, query: ListAvailableCompaniesQuery
    ) -> CompanyPageDTO | None: ...

    async def linked_contact_ids(
        self, tenant_id: EntityIdVO, company_id: CompanyIdVO
    ) -> tuple[ContactIdVO, ...]: ...


__all__ = ["CompanyQueryRepositoryProtocol"]
