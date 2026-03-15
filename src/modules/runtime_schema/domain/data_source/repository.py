from modules.runtime_schema.domain.data_source.entity import DataSourceEntity


class DataSourceRepository:

    def add(self, entity: DataSourceEntity) -> DataSourceEntity: ...
