from hashlib import sha256
import re
from secrets import token_urlsafe

from src.modules.feed_builder.domain.access_key.value_object.access_token_hash import (
    AccessTokenHashVO,
)

_TOKEN_FORMAT = re.compile(r"fba_[A-Za-z0-9_-]{43}")


def issue_access_token() -> tuple[str, AccessTokenHashVO]:
    """Генерирует 256-битный секрет и его сохраняемый digest."""
    token = f"fba_{token_urlsafe(32)}"
    return token, AccessTokenHashVO(sha256(token.encode("ascii")).digest())


def access_token_digest(token: str) -> AccessTokenHashVO | None:
    """Разбирает выданный формат без включения секрета в ошибки или логи."""
    if _TOKEN_FORMAT.fullmatch(token) is None:
        return None
    return AccessTokenHashVO(sha256(token.encode("ascii")).digest())
