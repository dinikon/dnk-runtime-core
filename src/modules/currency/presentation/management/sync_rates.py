from datetime import timedelta
from uuid import uuid4
import logging
from src.config import dnk_config
from src.modules.currency.application.provider.command.sync_provider_rates_command import (
    SyncProviderRatesCommand,
)
from src.modules.currency.application.provider.use_case.sync_provider_rates import (
    SyncProviderRates,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO
from src.modules.currency.infrastructure.persistence.rate_import.transactions import (
    ProviderImportTransactions,
)
from src.modules.currency.presentation.depends.infrastructure import (
    get_rate_source_catalog,
)
from src.modules.shared.infrastructure.persistence import db_helper
from src.modules.shared.infrastructure.time.utc_clock import UtcClock

logger = logging.getLogger(__name__)


async def sync_rates(args):
    clock = UtcClock()
    today = clock.now().date()
    start = args.date_from or today - timedelta(days=7)
    end = args.date_to or today + timedelta(days=1)
    if args.scheduled and not dnk_config.CURRENCY.nbu.sync_enabled:
        return 0
    registry = get_rate_source_catalog().registry
    service = SyncProviderRates(
        registry, ProviderImportTransactions(db_helper.session_factory), clock
    )
    try:
        result = await service(
            SyncProviderRatesCommand(
                RateImportIdVO(uuid4()), ProviderCode(args.provider), start, end
            )
        )
        print(
            f"Import {result.id}: {result.created_count} new, {result.updated_count} revised."
        )
        return 0
    except Exception:
        logger.exception("Currency provider import failed")
        return 1
    finally:
        await db_helper.engine.dispose()


__all__ = ["sync_rates"]
