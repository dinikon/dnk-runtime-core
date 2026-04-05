from dataclasses import dataclass

from src.modules.schema_registry.domain.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed


@dataclass(frozen=True, slots=True)
class ObjectSeed:
    name: str
    label: str
    description: str
    table_name: str
    fields: tuple[FieldSeed, ...]
    indexes: tuple[IndexSeed, ...] = ()
    relations: tuple[RelationSeed, ...] = ()
