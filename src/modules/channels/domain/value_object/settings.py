from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
from src.modules.channels.domain.error import InvalidChannelError


@dataclass(frozen=True, slots=True)
class ConnectionSettings:
    """Настройки и запечатанные credentials; открытых секретов в Domain нет."""

    public: Mapping[str, str]
    encrypted_secrets: str = field(repr=False)
    secret_fields: tuple[str, ...]

    def __post_init__(self):
        if not all(
            isinstance(k, str) and isinstance(v, str) for k, v in self.public.items()
        ):
            raise InvalidChannelError("Invalid public settings.")
        if not isinstance(self.encrypted_secrets, str) or not self.encrypted_secrets:
            raise InvalidChannelError("Sealed credentials are required.")
        if any(not isinstance(k, str) for k in self.secret_fields) or set(
            self.public
        ) & set(self.secret_fields):
            raise InvalidChannelError("Invalid credential fields.")
        object.__setattr__(self, "public", MappingProxyType(dict(self.public)))
        object.__setattr__(
            self, "secret_fields", tuple(sorted(set(self.secret_fields)))
        )
