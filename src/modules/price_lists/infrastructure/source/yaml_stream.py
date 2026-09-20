from copy import deepcopy
import json
import yaml
from yaml import events as ev
from yaml.nodes import ScalarNode
from src.modules.price_lists.domain.price_list.error import MappingValidationError


class BoundedYamlStream:
    """Ограничивает объём чтения между событиями сканера YAML."""

    def __init__(self, source, max_bytes, stop):
        self.source = source
        self.max_bytes = max_bytes
        self.stop = stop
        self.since_event = 0

    def read(self, size=-1):
        """Читает ограниченный фрагмент и проверяет отмену."""
        if self.stop and self.stop.is_set():
            raise InterruptedError("Parsing cancelled")
        data = self.source.read(min(size if size >= 0 else 16384, 16384))
        self.since_event += len(data)
        if self.since_event > self.max_bytes + 32768:
            raise MappingValidationError("YAML scalar size limit exceeded.")
        return data


class YamlRecords:
    """Потоковый YAML selector с ограниченными anchors и раскрытием aliases."""

    def __init__(self, source, item_path, max_bytes, stop=None):
        self.source = BoundedYamlStream(source, max_bytes, stop)
        self.events = iter(
            yaml.parse(
                self.source, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)
            )
        )
        self.target = item_path.split(".") if item_path else []
        self.max_bytes = max_bytes
        self.record_bytes = 0
        self.anchors = {}
        self.anchor_bytes = 0
        self.aliases = 0
        self.found = False
        self.scalar_loader = yaml.SafeLoader("")

    def next(self):
        """Учитывает размер события до построения записи."""
        event = next(self.events)
        self.source.since_event = 0
        self.record_bytes += 64
        if isinstance(event, ev.ScalarEvent):
            self.record_bytes += len(event.value.encode())
        if self.record_bytes > self.max_bytes:
            raise MappingValidationError("YAML record size limit exceeded.")
        return event

    def value(self, event, depth=0):
        """Собирает одно ограниченное значение с проверкой aliases."""
        if depth > 64:
            raise MappingValidationError("YAML nesting limit exceeded.")
        if isinstance(event, ev.AliasEvent):
            self.aliases += 1
            if self.aliases > 1000 or event.anchor not in self.anchors:
                raise MappingValidationError("YAML alias limit or unresolved anchor.")
            value, size = self.anchors[event.anchor]
            self.record_bytes += size
            if self.record_bytes > self.max_bytes:
                raise MappingValidationError("YAML alias expansion limit exceeded.")
            return deepcopy(value)
        if isinstance(event, ev.ScalarEvent):
            tag = event.tag or self.scalar_loader.resolve(
                ScalarNode, event.value, event.implicit
            )
            node = ScalarNode(tag, event.value)
            value = self.scalar_loader.construct_object(node, deep=True)
            # A long feed must not accumulate PyYAML constructed_objects.
            self.scalar_loader.constructed_objects.clear()
        elif isinstance(event, ev.MappingStartEvent):
            value = {}
            merges = []
            next_event = self.next()
            while not isinstance(next_event, ev.MappingEndEvent):
                tag = (
                    (
                        next_event.tag
                        or self.scalar_loader.resolve(
                            ScalarNode, next_event.value, next_event.implicit
                        )
                    )
                    if isinstance(next_event, ev.ScalarEvent)
                    else None
                )
                if tag == "tag:yaml.org,2002:merge":
                    inherited = self.value(self.next(), depth + 1)
                    inherited = (
                        inherited if isinstance(inherited, list) else [inherited]
                    )
                    if not all(isinstance(item, dict) for item in inherited):
                        raise MappingValidationError(
                            "YAML merge must contain mappings."
                        )
                    merges.extend(inherited)
                    next_event = self.next()
                    continue
                key = self.value(next_event, depth + 1)
                if not isinstance(key, (str, int, float, bool, type(None))):
                    raise MappingValidationError("YAML mapping key must be scalar.")
                value[key] = self.value(self.next(), depth + 1)
                next_event = self.next()
            if merges:
                combined = {}
                for inherited in reversed(merges):
                    combined.update(inherited)
                combined.update(value)
                value = combined
        elif isinstance(event, ev.SequenceStartEvent):
            value = []
            next_event = self.next()
            while not isinstance(next_event, ev.SequenceEndEvent):
                value.append(self.value(next_event, depth + 1))
                next_event = self.next()
        else:
            raise MappingValidationError("Invalid YAML value.")
        anchor = getattr(event, "anchor", None)
        if anchor:
            size = len(json.dumps(value, default=str).encode()) + 64
            self.anchor_bytes += size
            if self.anchor_bytes > self.max_bytes:
                raise MappingValidationError("YAML anchor storage limit exceeded.")
            self.anchors[anchor] = (deepcopy(value), size)
        return value

    def scan(self, event, path, depth=0):
        """Находит выбранную последовательность без накопления документа."""
        if depth > 64:
            raise MappingValidationError("YAML nesting limit exceeded.")
        if path == self.target:
            if not isinstance(event, ev.SequenceStartEvent):
                raise MappingValidationError("YAML item_path must select a list.")
            self.found = True
            index = 0
            while True:
                self.record_bytes = 0
                self.aliases = 0
                child = self.next()
                if isinstance(child, ev.SequenceEndEvent):
                    break
                index += 1
                value = self.value(child, depth + 1)
                yield index, value if isinstance(value, dict) else {}
        elif getattr(event, "anchor", None):
            self.record_bytes = 0
            self.value(event, depth)
        elif isinstance(event, ev.MappingStartEvent):
            while True:
                self.record_bytes = 0
                key_event = self.next()
                if isinstance(key_event, ev.MappingEndEvent):
                    break
                key = self.value(key_event, depth + 1)
                yield from self.scan(self.next(), path + [str(key)], depth + 1)
        elif isinstance(event, ev.SequenceStartEvent):
            while True:
                self.record_bytes = 0
                child = self.next()
                if isinstance(child, ev.SequenceEndEvent):
                    break
                yield from self.scan(child, path + ["[]"], depth + 1)
        else:
            self.record_bytes = 0
            self.value(event, depth)

    def rows(self):
        """Выдаёт записи и проверяет конец единственного YAML-документа."""
        try:
            if not isinstance(self.next(), ev.StreamStartEvent) or not isinstance(
                self.next(), ev.DocumentStartEvent
            ):
                raise MappingValidationError("Invalid YAML document.")
            yield from self.scan(self.next(), [])
            if not isinstance(self.next(), ev.DocumentEndEvent) or not isinstance(
                self.next(), ev.StreamEndEvent
            ):
                raise MappingValidationError("Expected one YAML document.")
            if not self.found:
                raise MappingValidationError("YAML item_path was not found.")
        finally:
            self.scalar_loader.dispose()


__all__ = ["YamlRecords"]
