from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListUomsQuery:
    """Запрашивает полный системный справочник единиц учёта без фильтров."""
