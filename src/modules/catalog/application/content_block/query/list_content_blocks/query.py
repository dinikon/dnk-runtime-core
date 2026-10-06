from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListContentBlocksQuery:
    """Читает определения блоков текущего tenant."""
