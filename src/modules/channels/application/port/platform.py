"""Контракт платформенного пакета без импорта его моделей в ядро."""

from dataclasses import dataclass, field
from typing import Protocol

from src.modules.channels.application.capability import Capability
from src.modules.channels.application.sync_run.port.source import (
    PublicationPage,
    PublicationObservation,
    PublicationCheckpoint,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationKind,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.value_object.resource_identity import (
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
    publication_parent_kind: PublicationKind | None = None


@dataclass(frozen=True, slots=True)
class ValidatedConnection:
    """Нормализованная конфигурация и сериализованный секрет для шифрования."""

    config: ConnectionConfigVO
    credentials: bytes | None = field(repr=False)
    currency: str = "UAH"
    locales: tuple[str, ...] = ("uk", "ru")


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

    async def read_publications(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        checkpoint: PublicationCheckpoint,
        parent_external_id: str | None = None,
    ) -> PublicationPage:
        """Выполняет один шаг обхода, возвращая конкретные общие снимки."""
        ...

    async def read_publication_dependencies(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        keys: tuple[tuple[str, str], ...],
    ) -> tuple[PublicationObservation, ...]:
        """Дозагружает изменяемое дерево перед сменой ролей публикаций."""
        ...


class PlatformRegistry(Protocol):
    """Реестр установленных платформ с открытым строковым kind."""

    def get(self, kind: str) -> Platform:
        """Возвращает пакет либо безопасную ошибку неизвестной платформы."""
        ...

    def manifests(self) -> tuple[PlatformManifest, ...]:
        """Возвращает декларации установленных пакетов."""
        ...
