from typing import Protocol

from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO


class CompanyRepositoryProtocol(Protocol):
    """Запись агрегата в текущем tenant и транзакции внешнего UoW."""

    async def add(self, company: CompanyEntity) -> None: ...

    async def get_for_update(self, company_id: CompanyIdVO) -> CompanyEntity | None: ...

    async def save(self, company: CompanyEntity) -> None: ...

    async def delete(self, company: CompanyEntity) -> None: ...
