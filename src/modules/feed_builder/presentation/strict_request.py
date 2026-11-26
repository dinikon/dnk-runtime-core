from pydantic import BaseModel, ConfigDict


class ClosedSchema(BaseModel):
    """Запрещает неизвестные свойства и неявное приведение типов HTTP-документа."""

    model_config = ConfigDict(extra="forbid", strict=True)
