from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Protocol
from collections.abc import AsyncIterator
from uuid import UUID


class StorageUnavailableError(Exception):
    """Внешнее хранилище временно недоступно."""


class StorageOwnershipError(Exception):
    """Контейнер или объект не принадлежит зарегистрированному хранилищу."""


class StorageConfigurationError(Exception):
    """Конфигурация подключения отсутствует либо тип провайдера не поддерживается."""


@dataclass(frozen=True, slots=True)
class StorageLocation:
    """Согласованные координаты контейнера, независимые от SDK."""

    tenant_id: UUID
    bucket_id: UUID
    bucket_name: str
    provider_kind: str
    config_ref: str


@dataclass(frozen=True, slots=True)
class StorageObject:
    """Технические сведения об объекте для проверки и очистки."""

    key: str
    modified_at: datetime
    size_bytes: int
    owned: bool


class FileContentStream(Protocol):
    """Управляемый асинхронный поток без инфраструктурных типов."""

    def __aiter__(self) -> AsyncIterator[bytes]:
        """Возвращает итератор порций содержимого."""
        ...

    async def __anext__(self) -> bytes:
        """Читает очередную порцию либо завершает поток."""
        ...

    async def aclose(self) -> None:
        """Освобождает ресурс, включая досрочное прекращение чтения."""
        ...


class StorageAdapterProtocol(Protocol):
    """Порт приватных контейнеров и объектов внешнего хранилища."""

    async def ensure_private_bucket(self, location: StorageLocation) -> None:
        """Идемпотентно создаёт контейнер и подтверждает владение и приватность."""
        ...

    async def put(
        self,
        location: StorageLocation,
        key: str,
        source: BinaryIO,
        size_bytes: int,
        content_type: str,
    ) -> int:
        """Записывает новый объект и возвращает фактически прочитанный размер."""
        ...

    async def open(self, location: StorageLocation, key: str) -> FileContentStream:
        """Открывает поток без формирования внешней ссылки."""
        ...

    def objects(self, location: StorageLocation) -> AsyncIterator[StorageObject]:
        """Перечисляет объекты порциями для обслуживания хранилища."""
        ...

    async def remove(self, location: StorageLocation, key: str) -> None:
        """Удаляет объект; его отсутствие считается успехом."""
        ...

    async def abort_incomplete(
        self, location: StorageLocation, older_than: datetime
    ) -> int:
        """Удаляет незавершённые передачи вне защитного интервала."""
        ...

    async def purge(self, location: StorageLocation) -> None:
        """Удаляет принадлежащий модулю контейнер со всем его содержимым."""
        ...


class StorageResolverProtocol(Protocol):
    """Выбирает адаптер по типу подключения и ссылке конфигурации."""

    def resolve(self, location: StorageLocation) -> StorageAdapterProtocol:
        """Возвращает адаптер либо ошибку конфигурации."""
        ...
