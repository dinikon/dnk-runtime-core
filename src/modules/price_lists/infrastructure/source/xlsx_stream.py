from collections import OrderedDict
from contextlib import ExitStack
from pathlib import PurePosixPath
import struct
import sys
import tempfile
import zipfile
from defusedxml.ElementTree import fromstring
from src.modules.price_lists.domain.price_list.error import MappingValidationError
from src.modules.price_lists.infrastructure.source.xml_stream import xml_records


class DiskStrings:
    """Общий словарь XLSX: дисковые offsets и ограниченный LRU в RAM."""

    def __init__(self, directory, cache_bytes, max_bytes):
        self.data = open(directory + "/strings.data", "w+b")
        self.index = open(directory + "/strings.idx", "w+b")
        self.cache = OrderedDict()
        self.cache_size = 0
        self.cache_bytes = cache_bytes
        self.max_bytes = max_bytes
        self.count = 0

    def append(self, value):
        """Добавляет запись в ограниченный дисковый индекс."""
        encoded = value.encode()
        offset = self.data.tell()
        if offset + len(encoded) + (self.count + 1) * 12 > self.max_bytes:
            raise MappingValidationError("Temporary storage budget exceeded.")
        self.data.write(encoded)
        self.index.write(struct.pack("<QI", offset, len(encoded)))
        self.count += 1

    def prepare(self):
        """Фиксирует буферы индекса перед чтением."""
        self.data.flush()
        self.index.flush()

    def get(self, index):
        """Читает aggregate текущего tenant и проверяет его наличие."""
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        if not 0 <= index < self.count:
            raise MappingValidationError("Invalid XLSX shared string reference.")
        self.index.seek(index * 12)
        offset, size = struct.unpack("<QI", self.index.read(12))
        self.data.seek(offset)
        value = self.data.read(size).decode()
        cost = sys.getsizeof(value) + 128
        while self.cache and self.cache_size + cost > self.cache_bytes:
            _, removed = self.cache.popitem(last=False)
            self.cache_size -= sys.getsizeof(removed) + 128
        if cost <= self.cache_bytes:
            self.cache[index] = value
            self.cache_size += cost
        return value

    def close(self):
        """Закрывает принадлежащие адаптеру файлы."""
        self.data.close()
        self.index.close()


class XlsxReader:
    """Читает ZIP/XML без materialization sharedStrings и worksheet."""

    def __init__(self, path, options, stop=None):
        self.path = path
        self.options = options
        self.stop = stop

    def archive(self):
        """Проверяет контейнер и ограничения распакованного XLSX."""
        # ZipFile materializes the central directory in its constructor; reject
        # an excessive directory before that allocation, including ZIP64 sentinels.
        with self.path.open("rb") as source:
            source.seek(0, 2)
            size = source.tell()
            source.seek(max(0, size - 65557))
            tail = source.read(65557)
        position = tail.rfind(b"PK\x05\x06")
        if position < 0 or position + 22 > len(tail):
            raise MappingValidationError("Invalid XLSX archive directory.")
        (
            _,
            disk,
            directory_disk,
            disk_entries,
            entries,
            directory_size,
            _,
            comment_size,
        ) = struct.unpack_from("<4s4H2LH", tail, position)
        if (
            disk
            or directory_disk
            or disk_entries != entries
            or entries > 10000
            or directory_size > 8 * 1024**2
            or position + 22 + comment_size != len(tail)
        ):
            raise MappingValidationError("XLSX archive directory limit exceeded.")
        try:
            archive = zipfile.ZipFile(self.path)
        except zipfile.BadZipFile:
            raise MappingValidationError("Invalid XLSX archive.") from None
        entries = archive.infolist()
        if (
            len(entries) > 10000
            or sum(e.file_size for e in entries) > self.options.max_uncompressed_bytes
        ):
            archive.close()
            raise MappingValidationError(
                "XLSX uncompressed size or entry limit exceeded."
            )
        return archive

    def metadata(self, archive):
        """Читает ограниченные метаданные листов и внутренних ссылок."""

        def read(name):
            """Читает ограниченный фрагмент и проверяет отмену."""
            with archive.open(name) as source:
                data = source.read(self.options.max_record_bytes + 1)
                if len(data) > self.options.max_record_bytes:
                    raise MappingValidationError("XLSX metadata size limit exceeded.")
                return fromstring(data)

        workbook = read("xl/workbook.xml")
        rels = read("xl/_rels/workbook.xml.rels")
        targets = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in rels
            if node.attrib.get("TargetMode") != "External"
        }
        sheets = {}
        for node in workbook.iter():
            if node.tag.rsplit("}", 1)[-1] == "sheet":
                rid = next(
                    (v for k, v in node.attrib.items() if k.rsplit("}", 1)[-1] == "id"),
                    None,
                )
                target = targets.get(rid, "")
                if not target:
                    raise MappingValidationError("Invalid XLSX worksheet relationship.")
                path = PurePosixPath(
                    target.lstrip("/") if target.startswith("/") else "xl/" + target
                )
                if ".." in path.parts:
                    raise MappingValidationError("Unsafe XLSX worksheet relationship.")
                sheets[node.attrib["name"]] = str(path)
        if not sheets:
            raise MappingValidationError("XLSX workbook has no sheets.")
        return sheets

    def rows(self, config, *, inspection=False):
        """Выдаёт строки выбранного листа с cached formula values."""
        with ExitStack() as stack:
            archive = stack.enter_context(self.archive())
            sheets = self.metadata(archive)
            name = config.get("sheet_name") or next(iter(sheets))
            if name not in sheets:
                raise MappingValidationError("Configured XLSX sheet does not exist.")
            directory = stack.enter_context(
                tempfile.TemporaryDirectory(prefix="dnk-xlsx-", dir=self.path.parent)
            )
            strings = DiskStrings(
                directory,
                self.options.string_cache_bytes,
                self.options.max_temp_bytes - self.path.stat().st_size,
            )
            stack.callback(strings.close)
            if "xl/sharedStrings.xml" in archive.namelist():
                with archive.open("xl/sharedStrings.xml") as source:
                    for node in xml_records(
                        source, "sst.si", self.options.max_record_bytes, self.stop
                    ):
                        strings.append(
                            "".join(
                                child.text or ""
                                for child in node.iter()
                                if child.tag == "t"
                            ).replace("x005F_", "")
                        )
                strings.prepare()
            header_row = int(config.get("header_row", 1))
            data_start = int(config.get("data_start_row", header_row + 1))
            headers = None
            count = 0
            with archive.open(sheets[name]) as source:
                for node in xml_records(
                    source,
                    "worksheet.sheetData.row",
                    self.options.max_record_bytes,
                    self.stop,
                ):
                    count += 1
                    number = int(node.attrib.get("r", count))
                    if number > 1048576:
                        raise MappingValidationError(
                            "XLSX worksheet row limit exceeded."
                        )
                    values = {}
                    next_column = 0
                    for cell in node:
                        if cell.tag != "c":
                            continue
                        reference = cell.attrib.get("r", "")
                        letters = "".join(c for c in reference if c.isalpha())
                        column = 0
                        for char in letters:
                            column = column * 26 + ord(char.upper()) - 64
                        column = column - 1 if letters else next_column
                        next_column = column + 1
                        if not 0 <= column < 256:
                            raise MappingValidationError("XLSX column limit exceeded.")
                        kind = cell.attrib.get("t", "n")
                        raw = next((c.text for c in cell if c.tag == "v"), None)
                        if kind == "s" and raw is not None:
                            value = strings.get(int(raw))
                        elif kind == "inlineStr":
                            value = "".join(
                                c.text or "" for c in cell.iter() if c.tag == "t"
                            )
                        elif kind == "b":
                            value = raw == "1" if raw is not None else None
                        elif kind == "e":
                            value = None
                        else:
                            value = raw
                        values[column] = value
                    if number == header_row:
                        headers = [
                            str(values.get(i) or "").strip()
                            for i in range(max(values, default=-1) + 1)
                        ]
                        if inspection:
                            yield 0, {"sheets": list(sheets), "columns": headers}
                            return
                    if number < data_start:
                        continue
                    if headers is None:
                        raise MappingValidationError("XLSX header row was not found.")
                    if all(v is None for v in values.values()):
                        continue
                    yield number, {
                        header: values.get(i) for i, header in enumerate(headers)
                    }
            if headers is None:
                raise MappingValidationError("XLSX header row was not found.")


__all__ = ["XlsxReader"]
