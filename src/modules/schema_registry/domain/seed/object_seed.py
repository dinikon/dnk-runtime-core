from dataclasses import dataclass

from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed


@dataclass(frozen=True, slots=True)
class ObjectSeed:
    """Raw seed-описание runtime-объекта, его полей, индексов и связей."""

    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    fields: tuple[FieldSeed, ...]
    indexes: tuple[IndexSeed, ...] = ()
    relations: tuple[RelationSeed, ...] = ()
