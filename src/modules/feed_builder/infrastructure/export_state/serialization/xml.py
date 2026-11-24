from datetime import datetime
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from xml.sax.saxutils import escape, quoteattr

from src.modules.feed_builder.application.feed.service.xml_document import (
    XmlDocumentSection,
    XmlElement,
)
from src.modules.feed_builder.application.feed.service.publication_export import (
    csv_cell,
    xml_attribute_cell,
)
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.types import ResolvedFieldValue
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)


class TemporaryXml:
    """Записывает подготовленные публикации в XML 1.0 с ограниченным буфером."""

    def __init__(
        self,
        settings: XmlExportSettingsVO,
        fields: tuple[FieldExportSettingsVO, ...],
        *,
        shop: bool = False,
        has_document_sections: bool = False,
        feed_name: str = "",
        as_of: datetime | None = None,
    ) -> None:
        """Открывает поток предложений и сохраняет форму документа."""
        self._shop = shop
        self._has_document_sections = has_document_sections
        self._sections: tuple[XmlDocumentSection, ...] = ()
        self._root = "yml_catalog" if shop else settings.root_name.value
        self._item = "offer" if shop else settings.item_name.value
        self._fields = fields
        self._feed_name = feed_name
        self._as_of = as_of
        self._file = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
        self._result = None
        self._finished = False
        if not has_document_sections:
            self._header(self._file)

    def document(self, sections: tuple[XmlDocumentSection, ...]) -> None:
        """Принимает элементы, подготовленные общим обходом полей."""
        self._sections = sections

    def write(self, row: tuple[ResolvedFieldValue, ...]) -> None:
        """Записывает атрибуты и элементы предложения в порядке схемы."""
        cells = tuple(zip(self._fields, row, strict=True))
        attributes = "".join(
            f" {field.name.value}={quoteattr(content)}"
            for field, value in cells
            if field.xml_placement is XmlFieldPlacement.ATTRIBUTE
            and (content := xml_attribute_cell(value)) is not None
        )
        self._file.write(f"  <{self._item}{attributes}>\n".encode("utf-8"))
        for field, value in cells:
            if value is None or field.xml_placement is XmlFieldPlacement.ATTRIBUTE:
                continue
            name = field.name.value
            attribute = ""
            if isinstance(value, PriceValueVO):
                if value.currency is not None:
                    attribute = f" currency={quoteattr(value.currency.value)}"
                content = format(value.amount.amount, "f")
            else:
                content = escape(csv_cell(value) or "", {"\r": "&#13;"})
            self._file.write(
                f"    <{name}{attribute}>{content}</{name}>\n".encode("utf-8")
            )
        self._file.write(f"  </{self._item}>\n".encode("utf-8"))

    def _header(self, output: BinaryIO) -> None:
        """Открывает XML и оболочку профиля, если она выбрана."""
        output.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        date = (
            f' date="{self._as_of:%Y-%m-%d %H:%M}"'
            if self._shop and self._as_of is not None
            else ""
        )
        output.write(f"<{self._root}{date}>\n".encode("utf-8"))
        self._write_sections(output, "ROOT")
        if self._shop:
            name = escape(self._feed_name)
            output.write(
                (
                    f"<shop>\n<name>{name}</name>\n<company>{name}</company>\n"
                    '<currencies><currency id="UAH" rate="1"/></currencies>\n'
                ).encode("utf-8")
            )

    def _write_sections(self, output: BinaryIO, parent: str) -> None:
        """Пишет структурированные узлы без знания их предметных типов."""
        for section in self._sections:
            if section.parent != parent:
                continue
            stack: list[XmlElement | str] = [section.element]
            while stack:
                item = stack.pop()
                if isinstance(item, str):
                    output.write(item.encode("utf-8"))
                    continue
                attributes = "".join(
                    f" {name}={quoteattr(value)}" for name, value in item.attributes
                )
                content = escape(item.text or "", {"\r": "&#13;"})
                output.write(f"<{item.name}{attributes}>{content}".encode("utf-8"))
                stack.append(f"</{item.name}>")
                stack.extend(reversed(item.children))
            output.write(b"\n")

    def upload_source(self) -> tuple[BinaryIO, int]:
        """Завершает файл, добавляя дерево перед уже записанными предложениями."""
        if not self._finished:
            if not self._has_document_sections:
                self._file.write(f"</{self._root}>\n".encode("utf-8"))
            else:
                self._result = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
                self._header(self._result)
                self._write_sections(self._result, "SHOP")
                if self._shop:
                    self._result.write(b"<offers>\n")
                self._file.seek(0)
                copyfileobj(self._file, self._result)
                if self._shop:
                    self._result.write(b"</offers>\n</shop>\n")
                self._result.write(f"</{self._root}>\n".encode("utf-8"))
            self._finished = True
        output = self._result if self._result is not None else self._file
        size = output.seek(0, 2)
        output.seek(0)
        return output, size

    def close(self) -> None:
        """Освобождает временные файлы."""
        self._file.close()
        if self._result is not None:
            self._result.close()
