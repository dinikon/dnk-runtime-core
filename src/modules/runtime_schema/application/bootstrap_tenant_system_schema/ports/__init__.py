from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
    RelationMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.schema_manager import (
    TenantSchemaManagerProtocol,
)
from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.system_definitions import (
    SystemObjectDefinitionsProviderProtocol,
)

__all__ = [
    "ObjectMetadataRepositoryProtocol",
    "FieldMetadataRepositoryProtocol",
    "RelationMetadataRepositoryProtocol",
    "TenantSchemaManagerProtocol",
    "SystemObjectDefinitionsProviderProtocol",
]
