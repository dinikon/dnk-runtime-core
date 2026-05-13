from __future__ import annotations

from typing import Protocol

from src.modules.communication.domain.message_template.entity import (
    MessageTemplate,
    TemplateVersion,
)
from src.modules.communication.domain.message_template.value_object import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.provider_connector.entity import (
    ProviderConnector,
    ProviderMessageType,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)
from src.modules.shared import EntityIdVO


class MessageTemplateRepositoryProtocol(Protocol):
    """Port for storing message template aggregate state."""

    async def load_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplate | None:
        """Loads one tenant message template by id."""
        ...

    async def load_template_by_code(
        self,
        *,
        tenant_id: EntityIdVO,
        template_code: str,
    ) -> MessageTemplate | None:
        """Loads one tenant message template by code."""
        ...

    async def save_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template: MessageTemplate,
    ) -> MessageTemplate:
        """Persists a message template and returns the stored entity."""
        ...

    async def list_templates(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[MessageTemplate]:
        """Lists tenant message templates."""
        ...

    async def load_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_version_id: TemplateVersionIdVO,
    ) -> TemplateVersion | None:
        """Loads one tenant template version by id."""
        ...

    async def load_active_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> TemplateVersion | None:
        """Loads the active version for a template, if any."""
        ...

    async def list_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> list[TemplateVersion]:
        """Lists all versions for a template."""
        ...

    async def save_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        version: TemplateVersion,
    ) -> TemplateVersion:
        """Persists one template version and returns the stored entity."""
        ...

    async def save_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        versions: list[TemplateVersion],
    ) -> list[TemplateVersion]:
        """Persists multiple template versions and returns stored entities."""
        ...


class MessageTemplateProviderLookupProtocol(Protocol):
    """Port for provider connector data needed by template rules."""

    async def load_provider_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> ProviderConnector | None:
        """Loads a provider connector by id."""
        ...

    async def load_provider_message_type(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
    ) -> ProviderMessageType | None:
        """Loads a provider message type by id."""
        ...


__all__ = [
    "MessageTemplateProviderLookupProtocol",
    "MessageTemplateRepositoryProtocol",
]
