from src.modules.shared.infrastructure.content.images import IMAGE_FILE_SUFFIXES
import hashlib
import hmac
import secrets
from urllib.parse import quote, urlsplit
from uuid import UUID

from src.modules.shared.application.crypto.cipher import Cipher


class EncryptedMediaTokens:
    """Случайные отзываемые токены, зашифрованные единственным Shared Cipher."""

    def __init__(self, *, cipher: Cipher, base_url: str) -> None:
        """Принимает канонический API host из Tenancy, а не пользовательский URL."""
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Media base URL must be an HTTPS origin.")
        self._cipher = cipher
        self._base_url = base_url.rstrip("/")

    def issue(self) -> tuple[bytes, bytes]:
        """Создаёт 256-битный секрет; открытое значение не хранится в агрегате."""
        token = secrets.token_urlsafe(32).encode("ascii")
        return hashlib.sha256(token).digest(), self._cipher.encrypt(token)

    def matches(self, token: str, expected: bytes) -> bool:
        """Проверяет фиксированную длину и сравнивает hash в постоянное время."""
        return len(token) == 43 and hmac.compare_digest(
            hashlib.sha256(token.encode("utf-8")).digest(), expected
        )

    def url(self, identifier: UUID, ciphertext: bytes, content_type: str) -> str:
        """Секрет находится только в query, уже скрываемом access logger проекта."""
        token = self._cipher.decrypt(ciphertext).decode("ascii")
        suffix = IMAGE_FILE_SUFFIXES[content_type]
        return f"{self._base_url}/api/channels/content-media/{identifier}/image.{suffix}?token={quote(token, safe='')}"
