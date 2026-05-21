from typing import Protocol

from src.modules.crm.application.company.dto import CompanyFieldsDescriptionDTO
from src.modules.crm.application.company.query.describe_company_fields_repository import (
    CompanyFieldsDescriptionRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class DescribeCompanyFieldsUseCaseProtocol(Protocol):
    """Порт use case описания полей компании."""

    async def __call__(self, tenant_id: EntityIdVO) -> CompanyFieldsDescriptionDTO:
        """Возвращает описание company и его полей для tenant."""
        ...


class DescribeCompanyFieldsUseCase:
    """Use case чтения описания CRM-модели company."""

    def __init__(
        self,
        repository: CompanyFieldsDescriptionRepositoryProtocol,
    ) -> None:
        """Инициализирует use case репозиторием описания company."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> CompanyFieldsDescriptionDTO:
        """Возвращает описание CRM-объекта company и его полей."""
        return await self._repository.describe_fields(tenant_id=tenant_id)
