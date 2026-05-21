from typing import Protocol

from src.modules.crm.application.company.dto.company_fields_description_dto import (
    CompanyFieldsDescriptionDTO,
)
from src.modules.shared import EntityIdVO


class CompanyFieldsDescriptionRepositoryProtocol(Protocol):
    """Порт чтения описания CRM-модели company."""

    async def describe_fields(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> CompanyFieldsDescriptionDTO:
        """Возвращает описание объекта company и его полей."""
        ...


__all__ = ["CompanyFieldsDescriptionRepositoryProtocol"]
