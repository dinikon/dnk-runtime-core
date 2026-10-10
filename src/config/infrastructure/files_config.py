from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings


class FilesSettings(BaseModel):
    """Instance-конфигурация закрытого системного MinIO."""

    model_config = ConfigDict(hide_input_in_errors=True)
    endpoint: str = ""
    access_key: SecretStr = Field(default=SecretStr(""), repr=False)
    secret_key: SecretStr = Field(default=SecretStr(""), repr=False)
    secure: bool = True
    region: str = ""
    timeout_seconds: float = Field(default=30, gt=0, le=60)
    operation_timeout_seconds: float = Field(default=600, gt=0, le=600)
    concurrency: int = Field(default=4, ge=1, le=32)


class FilesConfig(BaseSettings):
    """Включает файловые настройки в штатный проектный Config."""

    FILES: FilesSettings = Field(default_factory=FilesSettings)
