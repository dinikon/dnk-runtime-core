from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """Principal, восстановленный из валидной session."""

    user_id: str
    tenant_id: str | None
    session_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    is_authenticated: bool = True
