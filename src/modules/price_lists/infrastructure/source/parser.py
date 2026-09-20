from contextlib import aclosing, closing
import asyncio
import json
from pathlib import Path
from queue import Queue, Full, Empty
from threading import Event
from typing import Iterator
import yaml
import zipfile
from xml.sax import SAXException
from defusedxml.common import DefusedXmlException
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.application.sync_run.dto.parsed_row_dto import ParsedRow
from src.modules.price_lists.application.sync_run.dto.source_dto import SourceInspection
from src.modules.price_lists.domain.price_list.error import MappingValidationError
from src.modules.price_lists.domain.price_list.preset import prom_xml_config
from src.modules.price_lists.domain.offer.mapping import normalize_row
from src.modules.price_lists.infrastructure.source.xml_stream import (
    xml_records,
    element_values,
)
from src.modules.price_lists.infrastructure.source.yaml_stream import YamlRecords
from src.modules.price_lists.infrastructure.source.xlsx_stream import XlsxReader


class SourceParser:
    """Потоковые XML/YAML/XLSX adapters с backpressure и отменой."""

    def __init__(self, options: ImportOptions | None = None):
        self.options = options or ImportOptions()

    def raw_rows(self, path, source_format, config, stop=None):
        """Разбирает один источник без хранения документа целиком."""
        if source_format == "xml":
            with path.open("rb") as source:
                for index, node in enumerate(
                    xml_records(
                        source,
                        str(config.get("item_path") or ""),
                        self.options.max_record_bytes,
                        stop,
                    ),
                    1,
                ):
                    yield index, element_values(node)
        elif source_format == "yaml":
            with path.open("rb") as source:
                yield from YamlRecords(
                    source,
                    str(config.get("item_path") or ""),
                    self.options.max_record_bytes,
                    stop,
                ).rows()
        elif source_format == "xlsx":
            yield from XlsxReader(path, self.options, stop).rows(config)
        else:
            raise MappingValidationError("Unsupported source format.")

    def rows(
        self,
        path: Path,
        source_format: str,
        source_config: dict,
        mapping: dict,
        *,
        limit=None,
        stop=None,
    ) -> Iterator[ParsedRow]:
        """Синхронное ядро адаптера; async callers используют batches."""
        try:
            with closing(
                self.raw_rows(path, source_format, source_config, stop)
            ) as source:
                count = 0
                for number, raw in source:
                    if stop and stop.is_set():
                        return
                    count += 1
                    if count > self.options.max_rows:
                        raise MappingValidationError("Source row limit exceeded.")
                    values, errors = normalize_row(raw, mapping)
                    yield ParsedRow(number, values, errors)
                    if limit is not None and count >= limit:
                        return
        except (
            yaml.YAMLError,
            SAXException,
            DefusedXmlException,
            zipfile.BadZipFile,
            KeyError,
            ValueError,
            OverflowError,
        ) as exc:
            raise MappingValidationError("Invalid or unsafe source document.") from exc

    def inspect(self, path, source_format, source_config):
        """Ограниченное исследование структуры для preview."""
        if source_format == "xlsx":
            with closing(
                XlsxReader(path, self.options).rows(source_config, inspection=True)
            ) as rows:
                return next(rows)[1]
        paths = set()

        def collect(value, prefix="", depth=0):
            if depth > 64:
                return
            if isinstance(value, dict):
                for key, child in value.items():
                    if len(paths) >= 100:
                        return
                    name = f"{prefix}.{key}" if prefix else str(key)
                    paths.add(name)
                    collect(child, name, depth + 1)

        with closing(self.raw_rows(path, source_format, source_config)) as rows:
            for index, (_, raw) in enumerate(rows):
                collect(raw, str(source_config.get("item_path") or ""))
                if index >= 19:
                    break
        return {"paths": sorted(paths)}

    async def inspect_source(self, path, source_format, source_config):
        """Возвращает DTO структуры, не блокируя event loop."""
        result = await asyncio.to_thread(
            self.inspect, path, source_format, source_config
        )
        return SourceInspection(
            tuple(result.get("sheets", ())),
            tuple(result.get("columns", ())),
            tuple(result.get("paths", ())),
        )

    async def batches(self, path, source_format, source_config, mapping, *, limit=None):
        """Выдаёт ограниченные пакеты и завершает producer при закрытии."""
        queue = Queue(maxsize=self.options.parser_queue_batches)
        stop = Event()
        sentinel = object()

        def send(value):
            while not stop.is_set():
                try:
                    queue.put(value, timeout=0.05)
                    return
                except Full:
                    pass

        def producer():
            try:
                with closing(
                    self.rows(
                        path,
                        source_format,
                        source_config,
                        mapping,
                        limit=limit,
                        stop=stop,
                    )
                ) as source:
                    batch = []
                    size = 0
                    for row in source:
                        row_size = (
                            len(
                                json.dumps(
                                    row.normalized, default=str, ensure_ascii=False
                                ).encode()
                            )
                            + sum(len(e) for e in row.errors)
                            + 128
                        )
                        if batch and (
                            len(batch) >= self.options.batch_size
                            or size + row_size > self.options.batch_max_bytes
                        ):
                            send(batch)
                            batch = []
                            size = 0
                        if stop.is_set():
                            return
                        batch.append(row)
                        size += row_size
                    if batch:
                        send(batch)
            except BaseException as exc:
                send(exc)
            finally:
                send(sentinel)

        def receive():
            while not stop.is_set():
                try:
                    return queue.get(timeout=0.05)
                except Empty:
                    pass
            return sentinel

        task = asyncio.create_task(asyncio.to_thread(producer))
        try:
            while True:
                result = await asyncio.to_thread(receive)
                if result is sentinel:
                    break
                if isinstance(result, BaseException):
                    raise result
                yield result
        finally:
            stop.set()
            await asyncio.shield(task)


__all__ = ["SourceParser", "ParsedRow", "prom_xml_config"]
