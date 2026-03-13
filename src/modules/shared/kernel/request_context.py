from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared.kernel.principal import Principal


@dataclass(frozen=True, slots=True)
class RequestContext:
    principal: Principal | None
    request_id: str | None
    ip: str | None
    user_agent: str | None


__all__ = ["RequestContext"]
