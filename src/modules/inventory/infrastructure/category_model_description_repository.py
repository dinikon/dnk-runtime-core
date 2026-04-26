from __future__ import annotations

from src.modules.inventory.application.category.dto import (
    CategoryFieldDescriptionDTO,
    CategoryFieldOptionDTO,
    CategoryFieldsDescriptionDTO,
    CategoryObjectDescriptionDTO,
)
from src.modules.inventory.application.category.query.describe_category_fields_repository import (
    CategoryFieldsDescriptionRepositoryProtocol,
)
from src.modules.schema_registry.application.use_case.describe_runtime_object_use_case import (
    DescribeRuntimeObjectUseCaseProtocol,
)
from src.modules.shared import EntityIdVO


class CategoryModelDescriptionRepository(CategoryFieldsDescriptionRepositoryProtocol):
    """Inventory adapter чтения описания product_category через schema_registry."""

    _OBJECT_NAME = "product_category"

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
    ) -> CategoryFieldsDescriptionDTO:
        """Возвращает inventory-описание product_category."""
        description = await self._describe_runtime_object_use_case(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )
        return CategoryFieldsDescriptionDTO(
            object_description=CategoryObjectDescriptionDTO(
                id=description.id,
                singular_label=description.singular_label,
                plural_label=description.plural_label,
                description=description.description,
                kind=description.kind,
            ),
            fields=tuple(
                CategoryFieldDescriptionDTO(
                    id=field.id,
                    field_name=field.field_name,
                    label=field.label,
                    description=field.description,
                    type=field.type,
                    kind=field.kind,
                    is_nullable=field.is_nullable,
                    default_value=field.default_value,
                    options=tuple(
                        CategoryFieldOptionDTO(value=value, label=label)
                        for value, label in field.options.items()
                    ),
                )
                for field in description.fields
            ),
        )
