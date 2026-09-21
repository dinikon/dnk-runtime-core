from dataclasses import dataclass
from src.modules.currency.application.provider.dto.provider_capabilities import (
    ProviderCapabilities,
)
from src.modules.currency.application.provider.registry import (
    ExchangeRateProviderRegistry,
)
from src.modules.currency.domain.provider.error import RateSourceNotRegistered
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode


@dataclass(frozen=True, slots=True)
class RateSourceDTO:
    """A local or registered external source and its advertised capabilities."""

    code: ProviderCode
    capabilities: ProviderCapabilities
    local: bool


class RateSourceCatalog:
    """One catalog of local and registered external rate sources."""

    def __init__(self, registry: ExchangeRateProviderRegistry):
        self.registry = registry

    def list(self) -> tuple[RateSourceDTO, ...]:
        """Describe sources without executing provider I/O."""
        return (
            RateSourceDTO(
                ProviderCode("MANUAL"),
                ProviderCapabilities(True, False, None, False),
                True,
            ),
            *(
                RateSourceDTO(p.code, p.capabilities, False)
                for p in self.registry.providers.values()
            ),
        )

    def require(self, code: ProviderCode) -> RateSourceDTO:
        """Reject a policy referencing an unregistered source."""
        for source in self.list():
            if source.code == code:
                return source
        raise RateSourceNotRegistered(f"Rate source {code} is not registered.")


__all__ = ["RateSourceDTO", "RateSourceCatalog"]
