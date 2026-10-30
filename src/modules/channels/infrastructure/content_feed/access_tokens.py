import hashlib
import hmac
import secrets
from urllib.parse import quote
from uuid import UUID

from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.infrastructure.platforms.url import normalize_endpoint
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import CiphertextUnreadable


class EncryptedFeedTokens:
    """Отзывные секреты фида, зашифрованные единственным проектным Cipher."""

    def __init__(self, *, cipher: Cipher, base_url: str) -> None:
        """Получает origin из Tenancy, а не из произвольного заголовка запроса."""
        self._cipher, self._base_url = cipher, base_url

    def issue(self) -> tuple[bytes, bytes]:
        """Создаёт случайный 256-битный секрет."""
        token = secrets.token_urlsafe(32).encode("ascii")
        return hashlib.sha256(token).digest(), self._cipher.encrypt(token)

    def matches(self, token: str, expected: bytes) -> bool:
        """Сравнивает hash фиксированного по длине токена."""
        return len(token) == 43 and hmac.compare_digest(
            hashlib.sha256(token.encode()).digest(), expected
        )

    def url(self, identifier: UUID, ciphertext: bytes) -> str:
        """Отказывает при непубличном origin до включения внешней выдачи."""
        try:
            origin = normalize_endpoint(self._base_url)
        except ChannelInputError:
            raise FeedBuildError(
                "feed_public_origin_unavailable", unavailable=True
            ) from None
        try:
            token = self._cipher.decrypt(ciphertext).decode("ascii")
        except (CiphertextUnreadable, UnicodeError):
            raise FeedBuildError("feed_access_unreadable") from None
        return f"{origin}/api/channels/content-feeds/{identifier}/feed.xml?token={quote(token, safe='')}"
