from enum import StrEnum


class XmlFieldPlacement(StrEnum):
    """Определяет размещение поля внутри XML-предложения."""

    ELEMENT = "ELEMENT"
    ATTRIBUTE = "ATTRIBUTE"
