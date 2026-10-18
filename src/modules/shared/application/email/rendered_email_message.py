from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderedEmailMessage:
    """Уже собранное письмо, готовое к передаче в transport."""

    recipient_email: str
    subject: str
    text_body: str
    html_body: str | None = None


__all__ = ["RenderedEmailMessage"]
