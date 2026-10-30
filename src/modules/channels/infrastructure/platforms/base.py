"""Общие параметры Pydantic-моделей платформ."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Запрещает неизвестные поля и скрывает входные данные в ошибках."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, strict=True)


class StockSyncSettings(StrictModel):
    """Публичные настройки синхронизации без серверной ревизии и времени."""

    allow_export: bool = False
