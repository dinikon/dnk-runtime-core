from dataclasses import dataclass, field
from typing import Protocol

from src.modules.channels.application.capability import Capability
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class PlatformManifest:
    """Описание установленного пакета и форм подключения Console."""

    kind: str
    title: str
    config_version: int
    config_schema: JsonObject
    credentials_schema: JsonObject
    supported_capabilities: tuple[Capability, ...]


@dataclass(frozen=True, slots=True)
class ValidatedConnection:
    """Нормализованная конфигурация и настоящий секрет для Shared Cipher."""

    config: ConnectionConfigVO
    credentials: bytes | None = field(repr=False)


class Platform(Protocol):
    """Пакет владеет конкретными моделями и проверкой доступа к магазину."""

    manifest: PlatformManifest

    def validate(
        self, config: ConnectionConfigVO, credentials: JsonObject | None
    ) -> ValidatedConnection:
        """Проверяет настройки и явно сериализует credentials."""
        ...

    async def verify(
        self, config: ConnectionConfigVO, credentials: bytes
    ) -> ResourceIdentityVO:
        """Подтверждает идентичность магазина через внешний API."""
        ...


class PlatformRegistry(Protocol):
    """Выбирает установленный пакет по доверенному типу Channel."""

    def get(self, kind: str) -> Platform:
        """Возвращает пакет либо безопасную ошибку неизвестной платформы."""
        ...

    def manifests(self) -> tuple[PlatformManifest, ...]:
        """Возвращает декларации форм в стабильном порядке."""
        ...
