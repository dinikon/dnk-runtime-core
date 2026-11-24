from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class XmlElement:
    """Представляет готовый XML-узел без правил расчёта."""

    name: str
    attributes: tuple[tuple[str, str], ...] = ()
    text: str | None = None
    children: tuple["XmlElement", ...] = ()


@dataclass(frozen=True, slots=True)
class XmlDocumentSection:
    """Помещает подготовленный элемент в выбранную часть документа."""

    parent: Literal["ROOT", "SHOP"]
    element: XmlElement
