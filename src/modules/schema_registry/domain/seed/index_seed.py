from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexSeed:
    name: str
    fields: tuple[str, ...]
    is_unique: bool = False
