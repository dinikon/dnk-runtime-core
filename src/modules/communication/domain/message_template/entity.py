from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.message_template.error import (
    TemplateVersionNotFoundError,
)
from src.modules.communication.domain.message_template.value_object import (
    ChannelCodeVO,
    MessageClassVO,
    MessageTemplateCodeVO,
    MessageTemplateIdVO,
    MessageTemplateNameVO,
    TemplateStatusVO,
    TemplateVersionIdVO,
    TemplateVersionStatusVO,
    TemplateVersionTimestampVO,
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
class MessageTemplateEntity:
    """Доменная сущность шаблона сообщения, привязанного к tenant."""

    template_id: MessageTemplateIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO

    template_code: MessageTemplateCodeVO
    name: MessageTemplateNameVO
    description: str | None
    provider_connector_id: ProviderConnectorIdVO
    provider_message_type_id: ProviderMessageTypeIdVO
    channel_code: ChannelCodeVO
    message_class: MessageClassVO
    status: TemplateStatusVO

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
        channel_code: ChannelCodeVO | str,
        message_class: MessageClassVO | str,
        now: datetime,
    ) -> Self:
        """Создает черновой шаблон сообщения с едиными created_at/updated_at."""
        return cls(
            template_id=template_id,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            template_code=MessageTemplateCodeVO(template_code),
            name=MessageTemplateNameVO(name),
            description=description,
            provider_connector_id=provider_connector_id,
            provider_message_type_id=provider_message_type_id,
            channel_code=ChannelCodeVO(channel_code),
            message_class=MessageClassVO(message_class),
            status=TemplateStatusVO.DRAFT,
        )

    def ensure_message_type_binding(self, message_type: ProviderMessageType) -> None:
        """Проверяет, что provider message type соответствует binding шаблона."""
        if message_type.provider_connector_id != self.provider_connector_id:
            raise CommunicationValidationError(
                "Provider message type does not belong to provider connector."
            )
        if ChannelCodeVO(message_type.channel_code) != self.channel_code:
            raise CommunicationValidationError(
                "Template channel must match provider message type channel."
            )

    def mark_active(self, *, now: datetime) -> None:
        """Переводит шаблон в ACTIVE при активации версии."""
        if self.status == TemplateStatusVO.ACTIVE:
            return
        self.status = TemplateStatusVO.ACTIVE
        self.updated_at = now


@dataclass(slots=True)
class TemplateVersionEntity:
    """Доменная сущность версии шаблона сообщения."""

    template_version_id: TemplateVersionIdVO
    created_at: datetime
    activated_at: datetime | None

    template_id: MessageTemplateIdVO
    version: TemplateVersionTimestampVO
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: TemplateVersionStatusVO

    @classmethod
    def create(
        cls,
        *,
        template_version_id: TemplateVersionIdVO,
        template_id: MessageTemplateIdVO,
        version: datetime,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
        now: datetime,
    ) -> Self:
        """Создает черновую версию шаблона с DRAFT default."""
        return cls(
            template_version_id=template_version_id,
            created_at=now,
            activated_at=None,
            template_id=template_id,
            version=TemplateVersionTimestampVO(version),
            template_payload=dict(template_payload),
            variables_schema=dict(variables_schema),
            status=TemplateVersionStatusVO.DRAFT,
        )

    @property
    def is_active(self) -> bool:
        """Возвращает признак активной версии."""
        return self.status == TemplateVersionStatusVO.ACTIVE

    def ensure_belongs_to(self, template: MessageTemplateEntity) -> None:
        """Проверяет, что версия принадлежит переданному шаблону."""
        if self.template_id != template.template_id:
            raise TemplateVersionNotFoundError()

    def activate(self, *, now: datetime) -> None:
        """Переводит версию в ACTIVE и сохраняет время активации."""
        self.status = TemplateVersionStatusVO.ACTIVE
        self.activated_at = now

    def deprecate(self) -> None:
        """Переводит активную версию в DEPRECATED."""
        if not self.is_active:
            return
        self.status = TemplateVersionStatusVO.DEPRECATED


__all__ = [
    "MessageTemplateEntity",
    "TemplateVersionEntity",
]
