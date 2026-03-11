from dataclasses import dataclass

from modules.runtime_schema.domain.source.value_object import DataSourceIdVO


@dataclass(slots=True)
class DataSource:
    id: DataSourceIdVO
