from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListProductTypesQuery:
    """Читает схемы типов текущего tenant."""
