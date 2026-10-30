"""Возможности платформенных пакетов, объявляемые в manifest."""

from typing import Literal

type Capability = Literal[
    "verify_connection",
    "publications",
    "read_stock",
    "write_stock",
    "write_content",
    "content_feed",
    "apply_content_feed",
]
