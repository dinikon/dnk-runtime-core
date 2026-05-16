from typing import Protocol

from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared import EntityIdVO


class CompanyCommandRepositoryProtocol(Protocol):
    """Порт командного хранения CRM-компаний."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        company_id: CompanyIdVO,
    ) -> CompanyEntity | None:
        """Загружает компанию tenant по id или возвращает None."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        company: CompanyEntity,
    ) -> CompanyEntity:
        """Сохраняет компанию tenant и возвращает актуальную entity."""
        ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        company_id: CompanyIdVO,
    ) -> None:
        """Удаляет компанию tenant по id."""
        ...
