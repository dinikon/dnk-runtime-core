from dataclasses import dataclass
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
class ValidatedConfig:
    """Нормализованная конфигурация и коды для проверки общих справочников."""

    config: ConnectionConfigVO
    currency: str
    locales: tuple[str, ...]


class Platform(Protocol):
    """Пакет владеет конкретными моделями и проверкой доступа к магазину."""

    manifest: PlatformManifest

    def validate_config(self, config: ConnectionConfigVO) -> ValidatedConfig:
        """Нормализует только публичные настройки подключения."""
        ...

    def encode_credentials(self, credentials: JsonObject) -> bytes:
        """Проверяет полный комплект и сериализует настоящие значения секретов."""
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
