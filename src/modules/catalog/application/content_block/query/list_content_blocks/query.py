from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListContentBlocksQuery:
    """Вход сценария list_content_blocks; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    locale: str
    search: str = ""
    page: int = 1
    page_size: int = 20
