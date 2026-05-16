from typing import Protocol

from src.modules.crm.application.company.dto.company_dto import CompanyDTO
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared import EntityIdVO


class CompanyQueryRepositoryProtocol(Protocol):
    """Порт чтения компаний для CRM query use cases."""

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        company_id: CompanyIdVO,
    ) -> CompanyDTO | None:
        """Возвращает компанию tenant по id или None."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[CompanyDTO]:
        """Возвращает страницу компаний tenant."""
        ...


__all__ = ["CompanyQueryRepositoryProtocol"]
