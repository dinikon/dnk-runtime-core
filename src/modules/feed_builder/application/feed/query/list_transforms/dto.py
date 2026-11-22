from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransformItemDTO:
    """Описывает преобразование и конкретный тип его параметров."""

    operation: str
    label: str
    field_kinds: tuple[str, ...]
    parameter_kind: str


@dataclass(frozen=True, slots=True)
class ListTransformsResultDTO:
    """Передаёт поддержанные определения преобразований без их исполнения."""

    items: tuple[TransformItemDTO, ...]
