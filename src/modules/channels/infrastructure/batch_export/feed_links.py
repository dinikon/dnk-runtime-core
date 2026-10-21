import hashlib
import hmac
import ipaddress
from datetime import UTC, datetime
from uuid import UUID
from src.modules.shared.application.network.host import normalize_host
from src.modules.channels.domain.error import (
    ChannelsUnavailableError,
    ChannelsNotFoundError,
)


class ExportFeedLinks:
    """Подписывает один файл, tenant и срок; не предоставляет доступа к Console или API Prom."""

    def __init__(self, key: str) -> None:
        """Получает только производный HMAC ключ; общего домена у tenant нет."""
        self.signing_available = bool(key)
        self.key = hashlib.sha256(b"channels-feed-v1:" + key.encode()).digest()

    @staticmethod
    def origin(host: str) -> str:
        """Использует HTTPS для доменов и HTTP для локального зарегистрированного host."""
        normalized = normalize_host(host)
        if not normalized or normalized != host:
            return ""
        local = normalized == "localhost" or normalized.endswith(".localhost")
        try:
            address = ipaddress.ip_address(normalized)
            local = address.is_loopback
            if not local and not address.is_global:
                return ""
        except ValueError:
            if not local and "." not in normalized:
                return ""
        return ("http://" if local else "https://") + normalized

    def token(self, tenant_id: UUID, run_id: UUID, expires_at: datetime) -> str:
        """Выдаёт bearer capability только для указанного неизменяемого файла."""
        value = tenant_id.hex + "." + str(int(expires_at.timestamp()))
        signature = hmac.new(
            self.key, (value + "." + run_id.hex).encode(), hashlib.sha256
        ).hexdigest()
        return value + "." + signature

    def url(
        self, host: str, tenant_id: UUID, run_id: UUID, expires_at: datetime
    ) -> str:
        """Формирует публичный путь модуля с ID операции, без секрета подключения."""
        origin = self.origin(host)
        if not self.signing_available or not origin:
            raise ChannelsUnavailableError("batch_export_feed_unconfigured")
        return (
            origin
            + "/api/channels/batch-exports/"
            + str(run_id)
            + "/feed.xml?access="
            + self.token(tenant_id, run_id, expires_at)
        )

    def authorize(self, run_id: UUID, access: str, now: datetime) -> UUID:
        """Проверяет подмену tenant/run/срока до доступа к схеме или хранилищу."""
        if not self.signing_available:
            raise ChannelsNotFoundError("export_feed_not_found")
        try:
            tenant, expires, signature = access.split(".")
            tenant_id = UUID(hex=tenant)
            expiration = datetime.fromtimestamp(int(expires), UTC)
            expected = self.token(tenant_id, run_id, expiration)
            if expiration <= now or not hmac.compare_digest(access, expected):
                raise ValueError("expired")
        except (ValueError, OverflowError, OSError):
            raise ChannelsNotFoundError("export_feed_not_found") from None
        return tenant_id
