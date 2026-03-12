from typing import Protocol


class LinkCodeGeneratorPort(Protocol):
    def generate(self, *, length: int) -> str: ...
