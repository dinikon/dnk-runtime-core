from __future__ import annotations

from typing import Protocol

from src.modules.communication.domain.message_template.entity import (
    MessageTemplateEntity,
    TemplateVersionEntity,
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
    """Порт командного хранения message template aggregate."""

    async def load_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplateEntity | None:
        """Загружает шаблон tenant по id или возвращает None."""
        ...

    async def save_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template: MessageTemplateEntity,
    ) -> MessageTemplateEntity:
        """Сохраняет шаблон tenant и возвращает актуальную entity."""
        ...

    async def load_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_version_id: TemplateVersionIdVO,
    ) -> TemplateVersionEntity | None:
        """Загружает версию шаблона tenant по id или возвращает None."""
        ...

    async def list_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> list[TemplateVersionEntity]:
        """Возвращает все версии шаблона tenant."""
        ...

    async def save_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        version: TemplateVersionEntity,
    ) -> TemplateVersionEntity:
        """Сохраняет версию шаблона tenant и возвращает актуальную entity."""
        ...

    async def save_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        versions: list[TemplateVersionEntity],
    ) -> list[TemplateVersionEntity]:
        """Сохраняет несколько версий шаблона tenant."""
        ...


class MessageTemplateProviderLookupProtocol(Protocol):
    """Порт чтения provider данных, нужных правилам шаблонов."""

    async def load_provider_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> ProviderConnector | None:
        """Загружает provider connector по id."""
        ...

    async def load_provider_message_type(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
    ) -> ProviderMessageType | None:
        """Загружает provider message type по id."""
        ...


__all__ = [
    "MessageTemplateRepositoryProtocol",
    "MessageTemplateProviderLookupProtocol",
]
