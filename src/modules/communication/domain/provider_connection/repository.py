from __future__ import annotations

from typing import Protocol

from src.modules.communication.domain.provider_connection.entity import (
    ProviderConnectionEntity,
)
from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector.entity import ProviderConnector
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
)
from src.modules.shared import EntityIdVO


class ProviderConnectionRepositoryProtocol(Protocol):
    """Порт командного хранения provider connection aggregate."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connection_id: ProviderConnectionIdVO,
    ) -> ProviderConnectionEntity | None:
        """Загружает provider connection tenant по id или возвращает None."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        connection: ProviderConnectionEntity,
    ) -> ProviderConnectionEntity:
        """Сохраняет provider connection tenant и возвращает актуальную entity."""
        ...

    async def find_active(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        channel_code: str,
    ) -> ProviderConnectionEntity | None:
        """Ищет active provider connection по connector и channel."""
        ...

    async def has_usage(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connection_id: ProviderConnectionIdVO,
    ) -> bool:
        """Проверяет, есть ли outbound/delivery история по connection."""
        ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connection_id: ProviderConnectionIdVO,
    ) -> None:
        """Физически удаляет provider connection tenant."""
        ...


class ProviderConnectionProviderLookupProtocol(Protocol):
    """Порт чтения provider connector данных для правил подключения."""

    async def load_provider_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> ProviderConnector | None:
        """Загружает provider connector по id."""
        ...


__all__ = [
    "ProviderConnectionProviderLookupProtocol",
    "ProviderConnectionRepositoryProtocol",
]
