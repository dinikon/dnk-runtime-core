from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.message_template.enum import (
    TemplateStatus,
    TemplateVersionStatus,
)
from src.modules.communication.domain.message_template.error import (
    TemplateVersionNotFoundError,
)
from src.modules.communication.domain.message_template.value_object import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.provider_connector.entity import (
    ProviderMessageType,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class MessageTemplate:
    template_id: MessageTemplateIdVO
    tenant_id: EntityIdVO
    template_code: str
    name: str
    description: str | None
    provider_connector_id: ProviderConnectorIdVO
    provider_message_type_id: ProviderMessageTypeIdVO
    channel_code: str
    message_class: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        template_id: MessageTemplateIdVO,
        tenant_id: EntityIdVO,
        template_code: str,
        name: str,
        description: str | None,
        provider_connector_id: ProviderConnectorIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
        channel_code: str,
        message_class: str,
        now: datetime,
    ) -> Self:
        """Creates a draft message template with consistent timestamps."""
        return cls(
            template_id=template_id,
            tenant_id=tenant_id,
            template_code=template_code,
            name=name,
            description=description,
            provider_connector_id=provider_connector_id,
            provider_message_type_id=provider_message_type_id,
            channel_code=channel_code,
            message_class=message_class,
            status=TemplateStatus.DRAFT.value,
            created_at=now,
            updated_at=now,
        )

    def ensure_message_type_binding(self, message_type: ProviderMessageType) -> None:
        """Validates that provider message type belongs to this template binding."""
        if message_type.provider_connector_id != self.provider_connector_id:
            raise CommunicationValidationError(
                "Provider message type does not belong to provider connector."
            )
        if message_type.channel_code != self.channel_code:
            raise CommunicationValidationError(
                "Template channel must match provider message type channel."
            )

    def mark_active(self, *, now: datetime) -> None:
        """Marks template active when a version is activated."""
        if self.status == TemplateStatus.ACTIVE.value:
            return
        self.status = TemplateStatus.ACTIVE.value
        self.updated_at = now


@dataclass(slots=True)
class TemplateVersion:
    template_version_id: TemplateVersionIdVO
    template_id: MessageTemplateIdVO
    version_no: int
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        template_version_id: TemplateVersionIdVO,
        template_id: MessageTemplateIdVO,
        version_no: int,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
        now: datetime,
    ) -> Self:
        """Creates a draft template version."""
        return cls(
            template_version_id=template_version_id,
            template_id=template_id,
            version_no=version_no,
            template_payload=dict(template_payload),
            variables_schema=dict(variables_schema),
            status=TemplateVersionStatus.DRAFT.value,
            created_at=now,
            activated_at=None,
        )

    @property
    def is_active(self) -> bool:
        """Returns whether this version is currently active."""
        return self.status == TemplateVersionStatus.ACTIVE.value

    def ensure_belongs_to(self, template: MessageTemplate) -> None:
        """Validates that this version belongs to the given template."""
        if self.template_id != template.template_id:
            raise TemplateVersionNotFoundError()

    def activate(self, *, now: datetime) -> None:
        """Marks this version active and stores activation time."""
        self.status = TemplateVersionStatus.ACTIVE.value
        self.activated_at = now

    def deprecate(self) -> None:
        """Deprecates only currently active versions."""
        if not self.is_active:
            return
        self.status = TemplateVersionStatus.DEPRECATED.value


__all__ = [
    "MessageTemplate",
    "TemplateVersion",
]
