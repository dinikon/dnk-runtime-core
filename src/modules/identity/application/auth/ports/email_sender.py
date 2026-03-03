from __future__ import annotations

from typing import Protocol


class EmailSenderPort(Protocol):
    async def send_login_code(self, email: str, code: str) -> None: ...
