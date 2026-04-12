from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexSeed:
    """Raw seed-описание индекса runtime-таблицы."""

    name: str
    fields: tuple[str, ...]
    is_unique: bool = False
