from src.modules.inventory.domain.stock_document.value_object.write_off_reason import (
    WriteOffReasonVO,
)
import hashlib
import json
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.create_write_off_draft.command import (
    CreateWriteOffDraftCommand,
)


def decimal_text(value: Decimal) -> str:
    """Нормализует представление без округления в ambient Decimal context."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def write_off_creation_fingerprint(command: CreateWriteOffDraftCommand) -> str:
    """Сохраняет значимый порядок строк и исключает сгенерированные время/ID."""
    payload = dict(
        warehouse_id=str(command.warehouse_id),
        owner_id=str(command.owner_id),
        reason=WriteOffReasonVO(command.reason).value,
        lines=[
            dict(
                inventory_item_id=str(line.inventory_item_id),
                quantity=decimal_text(line.quantity),
                uom=line.uom.strip().upper(),
            )
            for line in command.lines
        ],
    )
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
