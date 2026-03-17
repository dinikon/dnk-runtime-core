from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostQuery:
    host: str


@dataclass(frozen=True, slots=True)
class ResolveTenantRequestContextByHostQuery:
    host: str


__all__ = [
    "ResolveTenantByHostQuery",
    "ResolveTenantRequestContextByHostQuery",
]
