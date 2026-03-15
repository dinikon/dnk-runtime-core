from src.modules.runtime_schema.domain.schema.entity import DataSourceEntity


class DataSourceRepository:

    def add(self, entity: DataSourceEntity) -> DataSourceEntity: ...
