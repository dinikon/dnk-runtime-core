from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelationSeed:
    name: str
    relation_type: str  # "many_to_one" | "one_to_one"
    source_field: str
    target_object: str
    target_field: str = "id"
    on_delete: str = "restrict"
