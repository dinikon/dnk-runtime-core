from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StartCloudAuthCommand:
    """Вход или привязка облачного аккаунта; silent разрешён только для входа."""

    host: str
    session_token: str | None
    flow_cookie: str | None
    purpose: str
    silent: bool = False
