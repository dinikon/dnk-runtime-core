from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
    ImportFieldMapping,
)


class ImportMappingRequest(BaseModel):
    """Одно сопоставление конкретного запроса настройки."""

    model_config = ConfigDict(extra="forbid")
    target: str = Field(max_length=64)
    source: str | None = Field(default=None, max_length=4096)
    constant: str | None = Field(default=None, max_length=10000)
    locale: str | None = Field(default=None, max_length=64)


class ConfigureCatalogImportRequest(BaseModel):
    """Полный подтверждаемый черновик параметров."""

    model_config = ConfigDict(extra="forbid")
    mappings: list[ImportMappingRequest] = Field(default_factory=list, max_length=500)
    mode: str = "create"
    clear_empty: bool = False
    default_locale: str = Field(default="uk", min_length=1, max_length=64)
    timezone: str = Field(default="Europe/Kyiv", max_length=100)
    encoding: str | None = None
    delimiter: str | None = None
    record_path: str | None = Field(default=None, max_length=4096)

    def to_configuration(self) -> ImportConfiguration:
        """Преобразует транспортный запрос в независимый VO."""
        return ImportConfiguration(
            **{
                **self.model_dump(exclude={"mappings"}),
                "mappings": tuple(
                    ImportFieldMapping(**m.model_dump()) for m in self.mappings
                ),
            }
        )
