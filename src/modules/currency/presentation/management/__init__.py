from datetime import date
from uuid import UUID
from src.modules.currency.presentation.management.sync_rates import sync_rates
from src.modules.currency.presentation.management.restore_activations import (
    restore_activations,
)


def register(subparsers):
    parser = subparsers.add_parser("currency", help="Currency management")
    commands = parser.add_subparsers(dest="currency_command")
    sync = commands.add_parser("sync-rates", help="Import global NBU rates")
    sync.add_argument(
        "--provider", default="NBU", help="Registered external source code"
    )
    sync.add_argument("--date-from", type=date.fromisoformat)
    sync.add_argument("--date-to", type=date.fromisoformat)
    sync.add_argument(
        "--scheduled", action="store_true", help="Honor the sync_enabled setting"
    )
    sync.set_defaults(handler=sync_rates)
    recover = commands.add_parser(
        "restore-activations", help="Restore pending functional currency activations"
    )
    recover.add_argument("--tenant-id", type=UUID)
    recover.set_defaults(handler=restore_activations)


__all__ = ["register", "sync_rates", "restore_activations"]
