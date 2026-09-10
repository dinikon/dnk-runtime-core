from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostQuery:
    """Query публичного resolve tenant по host."""

    host: str


__all__ = ["ResolveTenantByHostQuery"]
