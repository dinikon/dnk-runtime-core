from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO


@dataclass(frozen=True, slots=True)
class UpdateCatalogBindingCommand:
    """Конкретный вход сценария update_catalog_binding."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    group_id: UUID
    expected_revision: int
    items: tuple[BindingPairDTO, ...]
    catalog_token: str
    publication_token: str
    locale: str = "uk"
