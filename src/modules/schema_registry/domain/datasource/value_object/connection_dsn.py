from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class ConnectionDsnVO:
    value: str

    _ALLOWED_SCHEMES = {
        "postgres",
        "postgresql",
        "postgresql+asyncpg",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }

    def __post_init__(self) -> None:
        normalized = self.value.strip()

        if not normalized:
            raise ValueError("Connection DSN cannot be empty.")

        parsed = urlparse(normalized)

        if not parsed.scheme:
            raise ValueError("Connection DSN must contain a scheme.")

        if parsed.scheme not in self._ALLOWED_SCHEMES:
            raise ValueError(
                f"Unsupported DSN scheme '{parsed.scheme}'. "
                f"Allowed: {', '.join(sorted(self._ALLOWED_SCHEMES))}."
            )

        if not parsed.hostname:
            raise ValueError("Connection DSN must contain a hostname.")

        if not parsed.path or parsed.path == "/":
            raise ValueError("Connection DSN must contain a database name in path.")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
