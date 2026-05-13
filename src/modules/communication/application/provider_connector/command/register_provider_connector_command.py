from dataclasses import dataclass

from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class RegisterProviderConnectorCommand:
    """Команда регистрации provider connector из YAML."""

    tenant_id: EntityIdVO
    provider_connector_id: ProviderConnectorIdVO
    yaml_content: str


__all__ = ["RegisterProviderConnectorCommand"]
