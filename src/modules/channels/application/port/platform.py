"""Контракт платформенного пакета без импорта его моделей в ядро."""

from dataclasses import dataclass, field
from typing import Protocol

from src.modules.channels.application.capability import Capability
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)


@dataclass(frozen=True, slots=True)
class PlatformManifest:
    """Описание платформы для registry и формы Console."""

    kind: str
    title: str
    config_version: int
    config_schema: JsonObject
    credentials_schema: JsonObject
    supported_capabilities: tuple[Capability, ...]


@dataclass(frozen=True, slots=True)
class ValidatedConnection:
    """Нормализованная конфигурация и сериализованный секрет для шифрования."""

    config: ConnectionConfigVO
    credentials: bytes | None = field(repr=False)


class Platform(Protocol):
    """Фасад связывает типы настроек, credentials и verifier внутри пакета."""

    manifest: PlatformManifest

    def validate(
        self, config: ConnectionConfigVO, credentials: JsonObject | None
    ) -> ValidatedConnection:
        """Проверяет локальные модели, возвращая безопасную общую границу."""
        ...

    async def verify(
        self, config: ConnectionConfigVO, credentials: bytes
    ) -> ResourceIdentityVO:
        """Восстанавливает свои типы и проверяет API вне SQL-транзакции."""
        ...


class PlatformRegistry(Protocol):
    """Реестр установленных платформ с открытым строковым kind."""

    def get(self, kind: str) -> Platform:
        """Возвращает пакет либо безопасную ошибку неизвестной платформы."""
        ...

    def manifests(self) -> tuple[PlatformManifest, ...]:
        """Возвращает декларации установленных пакетов."""
        ...
