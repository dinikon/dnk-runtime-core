import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.post_write_off.command import (
    PostWriteOffCommand,
)
from src.modules.inventory.application.stock_document.write_off_creation_fingerprint import (
    decimal_text,
)


def write_off_posting_fingerprint(command: PostWriteOffCommand) -> str:
    """Нормализует Decimal и коды, исключая серверное время, actor и сгенерированные ID."""

    def normalize(value: object) -> object:
        """Строит каноническое представление доверенной типизированной команды."""
        if isinstance(value, Decimal):
            return decimal_text(value)
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        return (
            str(value) if not isinstance(value, (str, int, bool, type(None))) else value
        )

    payload = {
        "document_id": command.document_id,
        "expected_version": command.expected_version,
        "lines": [
            dict(asdict(line), uom=line.uom.strip().upper()) for line in command.lines
        ],
    }
    return hashlib.sha256(
        json.dumps(normalize(payload), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
