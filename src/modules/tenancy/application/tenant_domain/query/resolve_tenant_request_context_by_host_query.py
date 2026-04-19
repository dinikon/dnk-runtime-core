from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolveTenantRequestContextByHostQuery:
    """Query получения внутреннего tenant request context по host."""

    host: str


__all__ = ["ResolveTenantRequestContextByHostQuery"]
