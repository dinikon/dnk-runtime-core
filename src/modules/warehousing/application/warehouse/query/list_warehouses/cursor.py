import base64
import binascii
from dataclasses import dataclass
import json
from typing import Self
from uuid import UUID

from src.modules.warehousing.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListParametersError,
)
from src.modules.warehousing.domain.warehouse.error import InvalidWarehouseCodeError
from src.modules.warehousing.domain.warehouse.value_object.code import WarehouseCodeVO


@dataclass(frozen=True, slots=True)
class WarehouseListCursor:
    """Технический курсор последней пары code/UUID в стабильной сортировке."""

    code: str
    warehouse_id: UUID

    def encode(self) -> str:
        """Кодирует пару в URL-safe base64 без I/O."""
        payload = json.dumps(
            [self.code, str(self.warehouse_id)],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str) -> Self:
        """Проверяет ограниченный курсор и возвращает типизированную пару."""
        try:
            if not isinstance(value, str) or not 1 <= len(value) <= 1024:
                raise ValueError("Invalid cursor length.")
            payload = json.loads(
                base64.b64decode(
                    value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
                )
            )
            if (
                not isinstance(payload, list)
                or len(payload) != 2
                or not isinstance(payload[0], str)
                or not isinstance(payload[1], str)
                or WarehouseCodeVO(payload[0]).value != payload[0]
            ):
                raise ValueError("Invalid cursor fields.")
            return cls(payload[0], UUID(payload[1]))
        except (
            ValueError,
            TypeError,
            binascii.Error,
            UnicodeError,
            InvalidWarehouseCodeError,
        ) as exc:
            raise InvalidWarehouseListParametersError(
                "Некорректный cursor списка складов."
            ) from exc
