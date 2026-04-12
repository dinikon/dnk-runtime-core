from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostQuery:
    """Query публичного resolve tenant по host."""

    host: str


@dataclass(frozen=True, slots=True)
class ResolveTenantRequestContextByHostQuery:
    """Query получения внутреннего tenant request context по host."""

    host: str


__all__ = [
    "ResolveTenantByHostQuery",
    "ResolveTenantRequestContextByHostQuery",
]
