from functools import lru_cache
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.infrastructure.plugin.registry import PluginRegistry
from src.modules.channels.infrastructure.plugin.prom.factory import PromPluginFactory
from src.modules.channels.infrastructure.plugin.woocommerce.factory import (
    WooPluginFactory,
)


@lru_cache(maxsize=1)
def get_plugin_registry() -> PluginRegistryProtocol:
    """Регистрирует provider пакеты в единственной внешней точке сборки."""
    return PluginRegistry((PromPluginFactory(), WooPluginFactory()))
