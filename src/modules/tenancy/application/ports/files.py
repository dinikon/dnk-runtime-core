from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantStorageRegistrationDTO:
    """Результат регистрации tenant-хранилища в терминах Tenancy."""

    provider_id: UUID
    bucket_id: UUID


class TenantStorageProtocol(Protocol):
    """Изолирует Tenancy от внутренней модели и SDK файлового модуля."""

    async def register(self, tenant_id: UUID) -> TenantStorageRegistrationDTO:
        """Регистрирует системное хранилище в текущей транзакции."""
        ...

    async def provision(self, tenant_id: UUID) -> None:
        """Подготавливает ранее зарегистрированный приватный контейнер."""
        ...

    async def is_ready(self, tenant_id: UUID) -> bool:
        """Проверяет зафиксированную готовность tenant-хранилища."""
        ...

    async def purge(self, tenant_id: UUID) -> None:
        """Удаляет физические ресурсы перед удалением tenant-схемы."""
        ...
