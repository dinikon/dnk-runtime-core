from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.modules.communication.domain.message_template import (
    MessageTemplate,
    TemplateVersion,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderMessageType,
)


class MessageTemplateRepositoryProtocol(Protocol):
    async def get_connector(
        self,
        tenant_id: UUID,
        provider_connector_id: UUID,
    ) -> ProviderConnector | None: ...

    async def get_message_type(
        self,
        tenant_id: UUID,
        provider_message_type_id: UUID,
    ) -> ProviderMessageType | None: ...

    async def create_template(
        self,
        *,
        tenant_id: UUID,
        template_code: str,
        name: str,
        description: str | None,
        provider_connector_id: UUID,
        provider_message_type_id: UUID,
        channel_code: str,
        message_class: str,
        status: str = ...,
    ) -> MessageTemplate: ...

    async def get_template(
        self,
        *,
        tenant_id: UUID,
        template_id: UUID,
    ) -> MessageTemplate | None: ...

    async def create_template_version(
        self,
        *,
        tenant_id: UUID,
        template_id: UUID,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
    ) -> TemplateVersion: ...

    async def get_template_version(
        self,
        tenant_id: UUID,
        template_version_id: UUID,
    ) -> TemplateVersion | None: ...

    async def activate_template_version(
        self,
        *,
        tenant_id: UUID,
        template: MessageTemplate,
        version: TemplateVersion,
        now: datetime,
    ) -> TemplateVersion: ...

    async def list_templates(self, tenant_id: UUID) -> list[MessageTemplate]: ...

    async def get_active_template_version(
        self,
        tenant_id: UUID,
        template_id: UUID,
    ) -> TemplateVersion | None: ...


__all__ = ["MessageTemplateRepositoryProtocol"]
