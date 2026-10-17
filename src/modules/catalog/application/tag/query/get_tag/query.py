from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO


@dataclass(frozen=True, slots=True)
class GetTagQuery:
    """Явное чтение get_tag в доверенном tenant."""

    tenant_id: EntityIdVO
    tag_id: TagIdVO
    locale: str
