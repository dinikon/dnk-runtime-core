from src.modules.channels.application.port.registry import ChannelRegistryPort
from src.modules.channels.application.query.get_kind_config.query import (
    GetKindConfigQuery,
)


class GetKindConfigHandler:
    def __init__(self, registry: ChannelRegistryPort):
        self.registry = registry

    async def execute(self, query: GetKindConfigQuery):
        return self.registry.get(query.kind)
