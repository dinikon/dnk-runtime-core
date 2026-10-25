import csv
import io
from collections import Counter
from collections.abc import Iterator
from typing import BinaryIO
from defusedxml import ElementTree as SafeXML
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import Element, ParseError, tostring
from src.modules.catalog.application.catalog_import.contracts import (
    SourceDescription,
    SourceField,
    SourceRecord,
    SourceValues,
)
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError

csv.field_size_limit(4 * 1024 * 1024)


class CatalogXMLParser(SafeXML.DefusedXMLParser):
    """Распознаёт только инертную стандартную декларацию YML shops.dtd."""

    def defused_start_doctype_decl(
        self, name: str, sysid: str | None, pubid: str | None, has_internal_subset: int
    ) -> None:
        """Не загружает DTD и запрещает любые внутренние объявления/другие DTD."""
        if (
            name == "yml_catalog"
            and sysid == "shops.dtd"
            and pubid is None
            and not has_internal_subset
        ):
            return
        super().defused_start_doctype_decl(name, sysid, pubid, has_internal_subset)


def local_name(tag: str) -> str:
    """Возвращает подпись XML-тега, сохраняя URI в идентификаторах."""
    return tag.rsplit("}", 1)[-1]


def xml_values(element: Element) -> SourceValues:
    """Разворачивает поля записи, сохраняя массивы и имена param."""
    values: SourceValues = {}

    def visit(node: Element, path: str, depth: int) -> None:
        """Обходит ограниченное дерево одной записи."""
        if depth > 64 or len(values) > 2000:
            raise InvalidCatalogValueError(
                "XML-запись слишком глубока или содержит слишком много полей."
            )
        for name, value in node.attrib.items():
            values.setdefault(f"{path}/@{name}".lstrip("/"), []).append(value)
        children = list(node)
        if not children or local_name(node.tag) in {
            "description",
            "description_ua",
            "body",
        }:
            text = node.text or ""
            if children:
                text += "".join(
                    tostring(child, encoding="unicode") for child in children
                )
            values.setdefault(path or ".", []).append(text)
            return
        for child in children:
            suffix = child.tag
            if local_name(child.tag) == "param" and child.get("name"):
                suffix += f"[@name={child.get('name')}]"
            visit(child, f"{path}/{suffix}".lstrip("/"), depth + 1)

    visit(element, "", 0)
    return values


class CatalogImportParser:
    """Потоковый CSV и безопасный XML без eval/XPath и полной загрузки файла."""

    def __init__(self, max_records: int) -> None:
        """Принимает ограничение источника из внешней сборки."""
        self.max_records = max_records

    def inspect(
        self, source: BinaryIO, configuration: ImportConfiguration
    ) -> SourceDescription:
        """Распознаёт формат, диалект CSV либо реальные пути XML-записей."""
        source.seek(0)
        sample = source.read(65536)
        source.seek(0)
        if sample.lstrip(b"\xef\xbb\xbf\x00\xff\xfe \r\n\t").startswith(b"<"):
            candidates: Counter[str] = Counter()
            stack: list[str] = []
            parents: list[Element] = []
            try:
                for event, node in SafeXML.iterparse(
                    source,
                    events=("start", "end"),
                    parser=CatalogXMLParser(
                        forbid_dtd=True, forbid_entities=True, forbid_external=True
                    ),
                ):
                    if event == "start":
                        stack.append(node.tag)
                        parents.append(node)
                        if len(stack) > 64:
                            raise InvalidCatalogValueError(
                                "XML превышает допустимую глубину."
                            )
                    else:
                        candidates["/" + "/".join(stack)] += 1
                        if len(candidates) > 2000:
                            raise InvalidCatalogValueError(
                                "XML содержит слишком много различных путей."
                            )
                        stack.pop()
                        parents.pop()
                        node.clear()
                        if parents:
                            # Сам родитель сохраняется до своего end; уже разобранные
                            # дочерние элементы удаляются с ограничением памяти.
                            if len(parents[-1]) > 64:
                                del parents[-1][:-1]
                paths = tuple(
                    sorted(path for path, count in candidates.items() if count > 1)
                )
                if not paths:
                    paths = tuple(sorted(candidates))
                preferred = next(
                    (p for p in paths if p.endswith("/offers/offer")), None
                )
                if preferred is None:
                    preferred = next(
                        (
                            p
                            for p in paths
                            if local_name(p.rsplit("/", 1)[-1])
                            in {"item", "product", "record"}
                        ),
                        None,
                    )
                selected = configuration.record_path or preferred
                if selected is None and len(paths) == 1:
                    selected = paths[0]
                if selected is not None and selected not in candidates:
                    raise InvalidCatalogValueError("Выбранный узел отсутствует в XML.")
                return SourceDescription("xml", None, None, selected, paths, ())
            except (ParseError, DefusedXmlException) as error:
                raise InvalidCatalogValueError(
                    "Некорректный XML или запрещённый DTD/ENTITY."
                ) from error
        encoding = configuration.encoding
        if encoding is None:
            decoder = __import__("codecs").getincrementaldecoder("utf-8-sig")()
            try:
                decoder.decode(sample, final=False)
                encoding = "utf-8-sig"
            except UnicodeDecodeError:
                encoding = "cp1251"
        try:
            text = sample.decode(encoding, errors="replace")
            delimiter = configuration.delimiter
            if delimiter is None:
                try:
                    delimiter = csv.Sniffer().sniff(text, delimiters=",;\t").delimiter
                except csv.Error:
                    delimiter = ","
            wrapper = io.TextIOWrapper(source, encoding=encoding, newline="")
            try:
                headers = next(csv.reader(wrapper, delimiter=delimiter, strict=True))
            finally:
                wrapper.detach()
            if not headers or len(headers) > 2000:
                raise InvalidCatalogValueError(
                    "CSV должен содержать от 1 до 2000 столбцов."
                )
            return SourceDescription(
                "csv",
                encoding,
                delimiter,
                None,
                (),
                tuple(
                    SourceField(f"c:{i}", label or f"Столбец {i + 1}")
                    for i, label in enumerate(headers)
                ),
            )
        except (UnicodeError, csv.Error, StopIteration) as error:
            raise InvalidCatalogValueError(
                "Не удалось прочитать заголовки CSV."
            ) from error

    def records(
        self, source: BinaryIO, description: SourceDescription
    ) -> Iterator[SourceRecord]:
        """Выдаёт записи по одной и закрывает обёртки при остановке чтения."""
        source.seek(0)
        try:
            if description.format == "csv":
                wrapper = io.TextIOWrapper(
                    source, encoding=description.encoding or "utf-8-sig", newline=""
                )
                try:
                    reader = csv.reader(
                        wrapper, delimiter=description.delimiter or ",", strict=True
                    )
                    next(reader)
                    number = 0
                    for row in reader:
                        if not row or not any(v.strip() for v in row):
                            continue
                        number += 1
                        if number > self.max_records:
                            raise InvalidCatalogValueError(
                                "Превышен лимит записей импорта."
                            )
                        if len(row) > len(description.fields):
                            raise InvalidCatalogValueError(
                                f"CSV-запись {number}: число столбцов отличается от заголовка."
                            )
                        row.extend([""] * (len(description.fields) - len(row)))
                        yield SourceRecord(
                            number, {f"c:{i}": [value] for i, value in enumerate(row)}
                        )
                finally:
                    wrapper.detach()
            elif description.record_path:
                stack: list[str] = []
                parents: list[Element] = []
                inside = False
                number = 0
                for event, node in SafeXML.iterparse(
                    source,
                    events=("start", "end"),
                    parser=CatalogXMLParser(
                        forbid_dtd=True, forbid_entities=True, forbid_external=True
                    ),
                ):
                    if event == "start":
                        stack.append(node.tag)
                        parents.append(node)
                        if len(stack) > 64:
                            raise InvalidCatalogValueError(
                                "XML превышает допустимую глубину."
                            )
                        if "/" + "/".join(stack) == description.record_path:
                            inside = True
                    else:
                        path = "/" + "/".join(stack)
                        if path == description.record_path:
                            number += 1
                            if number > self.max_records:
                                raise InvalidCatalogValueError(
                                    "Превышен лимит записей импорта."
                                )
                            yield SourceRecord(number, xml_values(node))
                            inside = False
                        stack.pop()
                        parents.pop()
                        if not inside:
                            node.clear()
                            if parents:
                                parents[-1].remove(node)
        except (ParseError, DefusedXmlException, csv.Error, UnicodeError) as error:
            raise InvalidCatalogValueError(
                "Источник повреждён или не соответствует выбранным параметрам."
            ) from error
