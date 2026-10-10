from collections.abc import Callable, Mapping
from src.modules.files.application.port.storage import (
    StorageAdapterProtocol,
    StorageConfigurationError,
    StorageLocation,
)


class StorageResolver:
    """Расширяемый process-local реестр фабрик адаптеров без S3-типов в Application."""

    def __init__(
        self, factories: Mapping[tuple[str, str], Callable[[], StorageAdapterProtocol]]
    ) -> None:
        """Принимает внешнюю сборку адаптеров и конфигураций подключения."""
        self._factories = dict(factories)
        self._adapters: dict[tuple[str, str], StorageAdapterProtocol] = {}

    def resolve(self, location: StorageLocation) -> StorageAdapterProtocol:
        """Лениво создаёт клиент отдельно в каждом процессе."""
        key = (location.provider_kind, location.config_ref)
        if key not in self._factories:
            raise StorageConfigurationError("Storage provider is not supported.")
        if key not in self._adapters:
            self._adapters[key] = self._factories[key]()
        return self._adapters[key]
