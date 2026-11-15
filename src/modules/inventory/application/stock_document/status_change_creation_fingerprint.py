from src.modules.inventory.domain.stock_document.value_object.status_change_reason import (
    StatusChangeReasonVO,
)
import hashlib
import json
from decimal import Decimal
from src.modules.inventory.application.stock_document.command.create_status_change_draft.command import (
    CreateStatusChangeDraftCommand,
)


def decimal_text(value: Decimal) -> str:
    """Нормализует представление без округления в ambient Decimal context."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def status_change_creation_fingerprint(command: CreateStatusChangeDraftCommand) -> str:
    """Сохраняет значимый порядок строк и исключает сгенерированные время/ID."""
    payload = dict(
        warehouse_id=str(command.warehouse_id),
        owner_id=str(command.owner_id),
        reason=StatusChangeReasonVO(command.reason).value,
        target_status=command.target_status.value,
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
