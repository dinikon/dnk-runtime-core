from src.modules.schema_registry.presentation.http.config.relation.requests.create_relation_request import (
    CreateRelationRequestSchema,
)
from src.modules.schema_registry.presentation.http.config.relation.requests.delete_relation_request import (
    DeleteRelationRequestSchema,
)
from src.modules.schema_registry.presentation.http.config.relation.requests.list_object_relations_request import (
    ListObjectRelationsRequestSchema,
)
from src.modules.schema_registry.presentation.http.config.relation.requests.relation_request import (
    RelationRequestSchema,
)

__all__ = [
    "CreateRelationRequestSchema",
    "DeleteRelationRequestSchema",
    "ListObjectRelationsRequestSchema",
    "RelationRequestSchema",
]
