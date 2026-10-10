from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.error import (
    InvalidStorageStateError,
    SystemProviderImmutableError,
)


@dataclass(slots=True)
class StorageProvider:
    """Подключение к хранилищу без credentials и инфраструктурных клиентов."""

    id: EntityIdVO
    name: str
    kind: str
    is_system: bool
    config_ref: str

    @classmethod
    def create(
        cls,
        *,
        provider_id: EntityIdVO,
        name: str,
        kind: str,
        is_system: bool,
        config_ref: str,
    ) -> "StorageProvider":
        """Создаёт подключение и проверяет согласованность системной конфигурации."""
        cls._validate(name, kind, is_system, config_ref)
        return cls(provider_id, name, kind, is_system, config_ref)

    @classmethod
    def restore(
        cls,
        *,
        provider_id: EntityIdVO,
        name: str,
        kind: str,
        is_system: bool,
        config_ref: str,
    ) -> "StorageProvider":
        """Восстанавливает подключение с проверкой инвариантов."""
        cls._validate(name, kind, is_system, config_ref)
        return cls(provider_id, name, kind, is_system, config_ref)

    @staticmethod
    def _validate(name: str, kind: str, is_system: bool, config_ref: str) -> None:
        """Проверяет обязательные значения и источник системного MinIO."""
        if not name.strip() or len(name) > 200 or not kind or not config_ref:
            raise InvalidStorageStateError("Invalid storage provider.")
        if is_system and (kind != "minio" or config_ref != "system_minio"):
            raise InvalidStorageStateError("System provider must use instance MinIO.")

    def rename(self, name: str) -> None:
        """Запрещает изменение системного подключения пользователем."""
        if self.is_system:
            raise SystemProviderImmutableError("System provider is read only.")
        self._validate(name, self.kind, self.is_system, self.config_ref)
        self.name = name
