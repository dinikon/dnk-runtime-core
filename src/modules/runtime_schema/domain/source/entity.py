from dataclasses import dataclass


@dataclass(slots=True)
class DataSourceEntity:
    id: UUID
