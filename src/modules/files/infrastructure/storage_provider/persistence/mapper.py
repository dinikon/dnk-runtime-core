from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Any
from src.modules.files.domain.storage_provider.aggregate import StorageProvider
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel,
)


class StorageProviderMapper:
    """Преобразует представление хранения без I/O и предметных правил."""

    @staticmethod
    def to_domain(row: StorageProviderModel) -> StorageProvider:
        """Восстанавливает агрегат через его явную фабрику."""
        return StorageProvider.restore(
            provider_id=EntityIdVO.from_value(row.id),
            name=row.name,
            kind=row.kind,
            is_system=row.is_system,
            config_ref=row.config_ref,
        )

    @staticmethod
    def to_insert_values(aggregate: StorageProvider) -> dict[str, Any]:
        """Извлекает значения для записи без самостоятельного INSERT."""
        return {
            "id": aggregate.id.uuid,
            "name": aggregate.name,
            "kind": aggregate.kind,
            "is_system": aggregate.is_system,
            "config_ref": aggregate.config_ref,
        }

    @staticmethod
    def to_update_values(aggregate: StorageProvider) -> dict[str, Any]:
        """Извлекает сохраняемое состояние агрегата."""
        return StorageProviderMapper.to_insert_values(aggregate)
