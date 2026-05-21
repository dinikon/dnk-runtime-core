from __future__ import annotations

from src.modules.crm.application.company.dto import (
    CompanyFieldDescriptionDTO,
    CompanyFieldOptionDTO,
    CompanyFieldsDescriptionDTO,
    CompanyObjectDescriptionDTO,
)
from src.modules.crm.application.company.query.describe_company_fields_repository import (
    CompanyFieldsDescriptionRepositoryProtocol,
)
from src.modules.schema_registry.application.use_case.describe_runtime_object_use_case import (
    DescribeRuntimeObjectUseCaseProtocol,
)
from src.modules.shared import EntityIdVO


class CompanyModelDescriptionRepository(CompanyFieldsDescriptionRepositoryProtocol):
    """CRM-адаптер чтения описания company через schema_registry."""

    _OBJECT_NAME = "company"

    def __init__(
        self,
        describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseProtocol,
    ) -> None:
        """Инициализирует репозиторий generic use case описания объекта."""
        self._describe_runtime_object_use_case = describe_runtime_object_use_case

    async def describe_fields(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> CompanyFieldsDescriptionDTO:
        """Возвращает CRM-описание company, мапя schema_registry DTO."""
        description = await self._describe_runtime_object_use_case(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )
        return CompanyFieldsDescriptionDTO(
            object_description=CompanyObjectDescriptionDTO(
                id=description.id,
                singular_label=description.singular_label,
                plural_label=description.plural_label,
                description=description.description,
                kind=description.kind,
            ),
            fields=tuple(
                CompanyFieldDescriptionDTO(
                    id=field.id,
                    field_name=field.field_name,
                    label=field.label,
                    description=field.description,
                    type=field.type,
                    kind=field.kind,
                    is_nullable=field.is_nullable,
                    default_value=field.default_value,
                    options=tuple(
                        CompanyFieldOptionDTO(value=value, label=label)
                        for value, label in field.options.items()
                    ),
                )
                for field in description.fields
            ),
        )
