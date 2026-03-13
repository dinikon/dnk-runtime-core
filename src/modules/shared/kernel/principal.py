from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    tenant_id: str | None
    session_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    is_authenticated: bool = True


__all__ = ["Principal"]
