from __future__ import annotations

from src.modules.crm.application.contact.dto.contact_fields_description_dto import (
    ContactFieldDescriptionDTO,
    ContactFieldOptionDTO,
    ContactFieldsDescriptionDTO,
    ContactObjectDescriptionDTO,
)
from src.modules.crm.application.contact.query.describe_contact_fields_repository import (
    ContactFieldsDescriptionRepositoryProtocol,
)
from src.modules.schema_registry.application.use_case.describe_runtime_object_use_case import (
    DescribeRuntimeObjectUseCaseProtocol,
)
from src.modules.shared import EntityIdVO


class ContactModelDescriptionRepository(ContactFieldsDescriptionRepositoryProtocol):
    """CRM-адаптер чтения описания contact через schema_registry."""

    _OBJECT_NAME = "contact"

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
    ) -> ContactFieldsDescriptionDTO:
        """Возвращает CRM-описание contact, мапя schema_registry DTO."""
        description = await self._describe_runtime_object_use_case(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )
        return ContactFieldsDescriptionDTO(
            object_description=ContactObjectDescriptionDTO(
                id=description.id,
                singular_label=description.singular_label,
                plural_label=description.plural_label,
                description=description.description,
                kind=description.kind,
            ),
            fields=tuple(
                ContactFieldDescriptionDTO(
                    id=field.id,
                    field_name=field.field_name,
                    label=field.label,
                    description=field.description,
                    type=field.type,
                    kind=field.kind,
                    is_nullable=field.is_nullable,
                    default_value=field.default_value,
                    options=tuple(
                        ContactFieldOptionDTO(value=value, label=label)
                        for value, label in field.options.items()
                    ),
                )
                for field in description.fields
            ),
        )
