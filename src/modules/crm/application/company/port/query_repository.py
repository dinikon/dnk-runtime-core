from typing import Protocol

from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO


class CompanyQueryRepositoryProtocol(Protocol):
    """Чтение проекций компаний без восстановления агрегатов."""

    async def get_details(
        self, *, company_id: CompanyIdVO
    ) -> CompanyDetailsDTO | None: ...

    async def list_details(self) -> list[CompanyDetailsDTO]: ...
