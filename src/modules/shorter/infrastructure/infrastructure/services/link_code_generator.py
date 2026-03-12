from __future__ import annotations

import secrets
import string
from typing import Sequence

from modules.shorter.domain import LinkCodeLengthNotSupportedError


class LinkCodeGeneratorService:
    _ALLOWED_LENGTHS: frozenset[int] = frozenset({4, 6, 8, 16})
    _DEFAULT_ALPHABET = string.ascii_letters + string.digits

    def __init__(self, alphabet: Sequence[str] | str | None = None):
        self._alphabet = tuple(alphabet or self._DEFAULT_ALPHABET)
        if not self._alphabet:
            raise ValueError("alphabet cannot be empty")

    def generate(self, *, length: int) -> str:
        if length not in self._ALLOWED_LENGTHS:
            raise LinkCodeLengthNotSupportedError(length=length)
        return "".join(secrets.choice(self._alphabet) for _ in range(length))

    def generate_4(self) -> str:
        return self.generate(length=4)

    def generate_6(self) -> str:
        return self.generate(length=6)

    def generate_8(self) -> str:
        return self.generate(length=8)

    def generate_16(self) -> str:
        return self.generate(length=16)
