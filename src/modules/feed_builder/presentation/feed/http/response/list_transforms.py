from pydantic import BaseModel


class TransformResponse(BaseModel):
    """Передаёт типизированные возможности преобразования."""

    operation: str
    label: str
    field_kinds: tuple[str, ...]
    parameter_kind: str


class ListTransformsResponse(BaseModel):
    """Передаёт определения преобразований без исполнения."""

    items: tuple[TransformResponse, ...]
