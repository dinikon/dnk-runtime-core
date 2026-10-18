"""Initial and manual refresh of global reference catalogs."""

import argparse

from src.modules.reference_data.presentation.jobs.refresh import DATASETS, sync_dataset
from src.modules.shared.infrastructure.persistence.database_helper import db_helper


async def handle_sync(args: argparse.Namespace) -> int:
    await db_helper.initialize_for_startup()
    try:
        datasets = DATASETS if args.dataset == "all" else (args.dataset,)
        for dataset in datasets:
            version, count, _ = await sync_dataset(dataset, db_helper.session_factory)
            print(f"OK {dataset} version={version} rows={count}")
        return 0
    finally:
        await db_helper.dispose()


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("reference-data", help="Global reference catalogs")
    actions = parser.add_subparsers(dest="reference_data_command", required=True)
    sync = actions.add_parser("sync", help="Synchronize public reference catalogs")
    sync.add_argument("--dataset", choices=("all", *DATASETS), default="all")
    sync.set_defaults(handler=handle_sync)
