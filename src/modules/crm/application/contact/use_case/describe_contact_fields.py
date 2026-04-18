from typing import Protocol

from src.modules.crm.application.contact.dto.contact_fields_description_dto import (
    ContactFieldsDescriptionDTO,
)
from src.modules.crm.application.contact.query.describe_contact_fields_repository import (
    ContactFieldsDescriptionRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class DescribeContactFieldsUseCaseProtocol(Protocol):
    """Порт use case получения описания CRM-модели контакта."""

    async def __call__(self, tenant_id: EntityIdVO) -> ContactFieldsDescriptionDTO:
        """Возвращает описание contact и его полей для tenant."""
        ...


class DescribeContactFieldsUseCase:
    """Use case чтения описания CRM-модели contact."""

    def __init__(
        self,
        repository: ContactFieldsDescriptionRepositoryProtocol,
    ) -> None:
        """Инициализирует use case репозиторием описания contact."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> ContactFieldsDescriptionDTO:
        """Возвращает описание CRM-объекта contact и его полей."""
        return await self._repository.describe_fields(tenant_id=tenant_id)
