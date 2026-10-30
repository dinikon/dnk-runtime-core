from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.domain.channel.value_object.stock_sync_settings import (
    StockSyncSettingsVO,
)
from src.modules.channels.domain.types import JsonObject


class StockSyncSettingsDocument(BaseModel):
    """Конкретная SQL-форма настроек, включая только серверные метаданные."""

    model_config = ConfigDict(extra="forbid")
    allow_export: bool = Field(strict=True)
    revision: int = Field(strict=True, gt=0)
    changed_at: datetime

    def to_value(self) -> StockSyncSettingsVO:
        """Преобразует представление; проверки значений выполняет VO."""
        return StockSyncSettingsVO(
            allow_export=self.allow_export,
            revision=self.revision,
            changed_at=self.changed_at,
        )


def read_stock_sync_settings(settings: JsonObject) -> StockSyncSettingsDocument:
    """Читает обязательный раздел нового формата без fallback к колонкам Channel."""
    return StockSyncSettingsDocument.model_validate(settings["stock_sync"])


def platform_settings(settings: JsonObject) -> JsonObject:
    """Отделяет настройки платформы от локальной политики синхронизации."""
    return {key: value for key, value in settings.items() if key != "stock_sync"}


def public_settings(settings: JsonObject) -> JsonObject:
    """Выдаёт разрешение, скрывая служебное поколение и время изменения."""
    stock_sync = read_stock_sync_settings(settings)
    return {
        **platform_settings(settings),
        "stock_sync": {"allow_export": stock_sync.allow_export},
    }


def write_settings(settings: JsonObject, stock_sync: StockSyncSettingsVO) -> JsonObject:
    """Собирает единый JSON из конфигурации платформы и настроек подключения."""
    return {
        **settings,
        "stock_sync": StockSyncSettingsDocument(
            allow_export=stock_sync.allow_export,
            revision=stock_sync.revision,
            changed_at=stock_sync.changed_at,
        ).model_dump(mode="json"),
    }
