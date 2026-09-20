from collections import deque
from pathlib import Path
from xml.etree.ElementTree import Element
from xml.sax.handler import ContentHandler, feature_namespaces, feature_external_ges
from defusedxml.sax import make_parser
from src.modules.price_lists.domain.price_list.error import MappingValidationError


class RecordHandler(ContentHandler):
    """SAX собирает только один выбранный элемент с ограничением размера."""

    def __init__(self, target, max_bytes, stop=None):
        super().__init__()
        self.target = target
        self.max_bytes = max_bytes
        self.stop = stop
        self.path = []
        self.nodes = []
        self.ready = deque()
        self.size = 0
        self.paths = set()

    def startElementNS(self, name, qname, attrs):
        if self.stop and self.stop.is_set():
            raise InterruptedError("Parsing cancelled")
        self.path.append(name[1])
        if len(self.path) > 64:
            raise MappingValidationError("XML nesting limit exceeded.")
        if len(self.paths) < 100:
            self.paths.add(".".join(self.path))
        if self.nodes or self.path == self.target:
            node = Element(name[1], {key[1]: value for key, value in attrs.items()})
            self.size += (
                sum(len(k.encode()) + len(v.encode()) for k, v in node.attrib.items())
                + len(name[1])
                + 32
            )
            if self.size > self.max_bytes:
                raise MappingValidationError("Source record size limit exceeded.")
            if self.nodes:
                self.nodes[-1].append(node)
            self.nodes.append(node)

    def characters(self, content):
        if self.nodes:
            self.size += len(content.encode("utf-8"))
            if self.size > self.max_bytes:
                raise MappingValidationError("Source record size limit exceeded.")
            node = self.nodes[-1]
            node.text = (node.text or "") + content

    def endElementNS(self, name, qname):
        if self.nodes:
            node = self.nodes.pop()
            if not self.nodes:
                self.ready.append(node)
                self.size = 0
        self.path.pop()


def xml_records(source, target: str, max_bytes: int, stop=None):
    """Читает XML малыми блоками без накопления дерева документа."""
    handler = RecordHandler(target.split("."), max_bytes, stop)
    parser = make_parser()
    # Prom feeds declare a DTD; ignore it without resolving external content.
    parser.forbid_external = False
    parser.setFeature(feature_external_ges, False)
    parser.setFeature(feature_namespaces, True)
    parser.setContentHandler(handler)
    while block := source.read(32768):
        if stop and stop.is_set():
            return
        parser.feed(block)
        while handler.ready:
            yield handler.ready.popleft()
    parser.close()
    while handler.ready:
        yield handler.ready.popleft()


def element_values(node):
    """Переводит выбранный XML record в простые значения mapping."""
    result = {"@" + key: value for key, value in node.attrib.items()}
    for child in node:
        if child.tag not in result:
            result[child.tag] = element_values(child) if len(child) else child.text
    return result


__all__ = ["xml_records", "element_values", "RecordHandler"]
