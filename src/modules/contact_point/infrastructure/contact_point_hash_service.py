from __future__ import annotations

import hashlib

from src.modules.contact_point.application.ports import ContactPointHashPort


class ContactPointHashService(ContactPointHashPort):
    def hash(self, normalized_value: str) -> str:
        return hashlib.sha256(normalized_value.encode("utf-8")).hexdigest()


__all__ = ["ContactPointHashService"]
