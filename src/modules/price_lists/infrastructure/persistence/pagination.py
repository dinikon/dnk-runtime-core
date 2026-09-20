from datetime import datetime
from decimal import Decimal
import hashlib
import json
from uuid import UUID
from sqlalchemy import or_, and_
from src.modules.shared.application.pagination.cursor_codec import CursorCodec
from src.modules.shared.application.pagination.errors import InvalidCursorError


def cursor_fingerprint(query, scope):
    """Связывает cursor с tenant, фильтрами и сортировкой."""
    payload = dict(
        tenant=str(query.tenant_id),
        scope=scope,
        filters=query.filters,
        sort=query.sort,
        direction=query.direction,
        archived=getattr(query, "include_archived", False),
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def cursor_clause(query, scope, expression, id_column):
    """Строит NULLS LAST keyset с устойчивым UUID tie-breaker."""
    if (
        query.pagination not in ("offset", "cursor")
        or query.direction not in ("asc", "desc")
        or not 1 <= query.limit <= 200
        or query.offset < 0
    ):
        raise InvalidCursorError("Invalid pagination parameters.")
    if query.pagination == "offset" and query.cursor is not None:
        raise InvalidCursorError("Cursor requires cursor pagination.")
    if query.pagination == "cursor" and query.offset:
        raise InvalidCursorError("Cursor pagination cannot use offset.")
    if not query.cursor:
        return None
    if len(query.cursor) > 4096:
        raise InvalidCursorError("Cursor is too long.")
    try:
        payload = CursorCodec.decode(query.cursor)
        if payload.get("version") != 1 or payload.get(
            "fingerprint"
        ) != cursor_fingerprint(query, scope):
            raise InvalidCursorError("Cursor does not match this query.")
        last_id = UUID(payload["id"])
        value = payload["value"]
        if value is None:
            return and_(expression.is_(None), id_column > last_id)
        kind = expression.type.python_type
        if kind is datetime:
            value = datetime.fromisoformat(value)
            if value.tzinfo is None:
                raise InvalidCursorError("Invalid timestamp cursor.")
        elif kind is Decimal:
            value = Decimal(value)
            if not value.is_finite():
                raise InvalidCursorError("Invalid numeric cursor.")
        elif kind is str:
            if not isinstance(value, str):
                raise InvalidCursorError("Invalid string cursor.")
        else:
            value = kind(value)
        comparison = (
            expression > value if query.direction == "asc" else expression < value
        )
        return or_(
            comparison,
            and_(expression == value, id_column > last_id),
            expression.is_(None),
        )
    except (ValueError, TypeError, KeyError, ArithmeticError):
        raise InvalidCursorError("Invalid cursor.") from None


def encode_cursor(query, scope, value, identifier):
    """Кодирует позицию последней выданной строки."""
    return CursorCodec.encode(
        dict(
            version=1,
            fingerprint=cursor_fingerprint(query, scope),
            value=value,
            id=str(identifier),
        )
    )


__all__ = ["cursor_clause", "encode_cursor", "cursor_fingerprint"]
