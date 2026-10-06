from src.modules.channels.application.port.registry import ChannelRegistryPort
from src.modules.channels.application.query.list_kinds.query import ListKindsQuery


class ListKindsHandler:
    def __init__(self, registry: ChannelRegistryPort):
        self.registry = registry

    async def execute(self, query: ListKindsQuery):
        return self.registry.list_all()
