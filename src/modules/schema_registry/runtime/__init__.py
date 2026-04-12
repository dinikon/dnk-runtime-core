from src.modules.schema_registry.runtime.descriptor import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
    RuntimeRelationDescriptor,
)
from src.modules.schema_registry.runtime.resolver import (
    RuntimeObjectResolverProtocol,
    SchemaRegistryRuntimeObjectResolver,
)

__all__ = [
    "RuntimeFieldDescriptor",
    "RuntimeObjectDescriptor",
    "RuntimeObjectResolverProtocol",
    "RuntimeRelationDescriptor",
    "SchemaRegistryRuntimeObjectResolver",
]
