from datetime import date, timedelta
import logging

from src.config import dnk_config
from src.modules.shared.infrastructure.persistence import db_helper
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.currency.application.provider import (
    ExchangeRateProviderRegistry,
    SyncProviderRates,
)
from src.modules.currency.domain.models import ProviderCode
from src.modules.currency.infrastructure.providers.nbu.client import NbuClient
from src.modules.currency.infrastructure.providers.nbu.adapter import NbuAdapter
from src.modules.currency.infrastructure.persistence.provider_writer import (
    ProviderImportTransactions,
)

logger = logging.getLogger(__name__)


async def sync_rates(args):
    clock = UtcClock()
    today = clock.now().date()
    start = args.date_from or today - timedelta(days=7)
    end = args.date_to or today + timedelta(days=1)
    if args.scheduled and not dnk_config.CURRENCY.nbu.sync_enabled:
        return 0
    registry = ExchangeRateProviderRegistry()
    registry.register(NbuAdapter(NbuClient(dnk_config.CURRENCY.nbu)))
    service = SyncProviderRates(
        registry, ProviderImportTransactions(db_helper.session_factory), clock
    )
    try:
        result = await service(
            provider=ProviderCode("NBU"), start_date=start, end_date=end
        )
        print(
            f"Import {result['id']}: {result['created_count']} new, {result['updated_count']} revised."
        )
        return 0
    except Exception:
        logger.exception("Currency provider import failed")
        return 1
    finally:
        await db_helper.engine.dispose()


def register(subparsers):
    parser = subparsers.add_parser("currency", help="Currency management")
    commands = parser.add_subparsers(dest="currency_command")
    sync = commands.add_parser("sync-rates", help="Import global NBU rates")
    sync.add_argument("--date-from", type=date.fromisoformat)
    sync.add_argument("--date-to", type=date.fromisoformat)
    sync.add_argument(
        "--scheduled", action="store_true", help="Honor the sync_enabled setting"
    )
    sync.set_defaults(handler=sync_rates)
