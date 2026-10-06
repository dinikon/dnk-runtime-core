from typing import Protocol


class RichTextSanitizerPort(Protocol):
    def clean(self, value: str) -> str: ...
