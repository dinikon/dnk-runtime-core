from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared.domain.identity_context.principal import Principal


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Контекст текущего request с principal и диагностическими metadata."""

    principal: Principal | None
    request_id: str | None
    ip: str | None
    user_agent: str | None


__all__ = ["RequestContext"]
