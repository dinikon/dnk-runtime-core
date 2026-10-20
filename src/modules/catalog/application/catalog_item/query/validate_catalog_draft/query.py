from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
)


@dataclass(frozen=True, slots=True)
class ValidateCatalogDraftQuery:
    """Задаёт типизированный вход сценария validate_catalog_draft."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    values: CreateCatalogItemValues
