import enum


class DataSourceTypeVO(str, enum.Enum):
    """Поддержанные backend-типы datasource для schema_registry."""

    POSTGRES = "postgres"
