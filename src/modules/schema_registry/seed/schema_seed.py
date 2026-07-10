from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.seed.contexts.communication import (
    COMMUNICATION_OBJECTS,
)
from src.modules.schema_registry.seed.contexts.contact_point import (
    CONTACT_POINT_OBJECTS,
)
from src.modules.schema_registry.seed.contexts.workflow import WORKFLOW_OBJECTS

SCHEMA_SEED = SchemaSeed(
    version=None,
    code="crm",
    label="CRM",
    objects=(
        *CONTACT_POINT_OBJECTS,
        *WORKFLOW_OBJECTS,
        *COMMUNICATION_OBJECTS,
    ),
)


__all__ = [
    "COMMUNICATION_OBJECTS",
    "CONTACT_POINT_OBJECTS",
    "SCHEMA_SEED",
    "WORKFLOW_OBJECTS",
]
