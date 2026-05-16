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
from src.modules.runtime_data.application.query.capabilities import (
    FieldQueryCapability,
    QueryCapabilityResolver,
    disabled_filter_capability,
    disabled_sort_capability,
)
from src.modules.schema_registry.application.use_case.describe_runtime_object_use_case import (
    DescribeRuntimeObjectUseCaseProtocol,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class ContactModelDescriptionRepository(ContactFieldsDescriptionRepositoryProtocol):
    """CRM-адаптер чтения описания contact через schema_registry."""

    _OBJECT_NAME = "contact"

    def __init__(
        self,
        describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseProtocol,
        runtime_object_resolver: RuntimeObjectResolverProtocol | None = None,
        query_capability_resolver: QueryCapabilityResolver | None = None,
    ) -> None:
        """Инициализирует репозиторий generic use case описания объекта."""
        self._describe_runtime_object_use_case = describe_runtime_object_use_case
        self._runtime_object_resolver = runtime_object_resolver
        self._query_capability_resolver = (
            query_capability_resolver or QueryCapabilityResolver()
        )

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
        capabilities_by_field = await self._capabilities_by_field(
            tenant_id=tenant_id,
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
                    filter=capabilities_by_field.get(
                        field.field_name,
                        _DEFAULT_FIELD_QUERY_CAPABILITY,
                    ).filter,
                    sort=capabilities_by_field.get(
                        field.field_name,
                        _DEFAULT_FIELD_QUERY_CAPABILITY,
                    ).sort,
                )
                for field in description.fields
            ),
        )

    async def _capabilities_by_field(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> dict[str, FieldQueryCapability]:
        if self._runtime_object_resolver is None:
            return {}
        descriptor = await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )
        return {
            capability.field_name: capability
            for capability in self._query_capability_resolver.resolve_for_descriptor(
                descriptor
            )
        }


_DEFAULT_FIELD_QUERY_CAPABILITY = FieldQueryCapability(
    field_name="",
    filter=disabled_filter_capability(),
    sort=disabled_sort_capability(),
)
