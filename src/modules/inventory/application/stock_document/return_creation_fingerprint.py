from src.modules.inventory.application.stock_document.write_off_creation_fingerprint import (
    decimal_text,
)
import hashlib, json
from src.modules.inventory.application.stock_document.command.create_return_draft.command import (
    CreateReturnDraftCommand,
)


def return_creation_fingerprint(command: CreateReturnDraftCommand) -> str:
    """Фиксирует основание и исходный состав без подписей или текущего остатка."""
    payload = {
        "origin_execution_id": str(command.origin_execution_id),
        "reason": command.reason.strip(),
        "lines": [
            {
                "origin_execution_line_id": str(v.origin_execution_line_id),
                "quantity": decimal_text(v.quantity),
                "uom": v.uom,
            }
            for v in command.lines
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
