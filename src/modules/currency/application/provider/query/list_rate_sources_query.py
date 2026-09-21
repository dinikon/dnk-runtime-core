from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListRateSourcesQuery:
    """Request the registered rate source catalog."""


__all__ = ["ListRateSourcesQuery"]
