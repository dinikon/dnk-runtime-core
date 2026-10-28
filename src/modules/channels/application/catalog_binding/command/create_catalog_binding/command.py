from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO


@dataclass(frozen=True, slots=True)
class CreateCatalogBindingCommand:
    """Конкретный вход сценария create_catalog_binding."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    catalog_root_id: UUID
    mode: BindingMode
    publication_root_id: UUID | None
    items: tuple[BindingPairDTO, ...]
    catalog_token: str
    publication_token: str
    locale: str = "uk"
