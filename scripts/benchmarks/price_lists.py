"""Reproducible, disposable PostgreSQL benchmark; run inside a 1 GiB container.

TEST_POSTGRES_URL must point to a disposable database. Schemas and jobs created by
this program are removed in finally. Fixtures are synthetic and generated on disk.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import tempfile
import time
import zipfile

from sqlalchemy import event, text, update, select, delete, insert
from test.test_price_list_bulk_postgres import PriceListBulkPostgresTests
from src.modules.price_lists.application.sync_run.dto.source_dto import FetchResult
from src.modules.price_lists.infrastructure.source.parser import SourceParser
from src.modules.price_lists.infrastructure.persistence.models import (
    PartnerOfferModel,
    PartnerOfferStateModel,
)
from src.modules.price_lists.presentation.jobs.handler import PriceListSyncJobHandler
from src.modules.shared.infrastructure.jobs.worker import ScheduledJobWorker
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


def write_xml(path, rows, *, changed=False):
    with path.open("w") as out:
        out.write("<yml_catalog><shop><offers>")
        for i in range(rows):
            price = "11" if changed and i % 100 == 0 else "10"
            out.write(
                f'<offer id="{i}" available="true"><vendorCode>SKU-{i}</vendorCode><name>Offer {i}</name><price>{price}</price><priceRRP>20</priceRRP><currencyId>UAH</currencyId></offer>'
            )
        out.write("</offers></shop></yml_catalog>")


def write_yaml(path, rows):
    with path.open("w") as out:
        out.write("offers:\n")
        for i in range(rows):
            out.write(
                f'  - {{external_id: "{i}", sku: "SKU-{i}", title: "Offer {i}", purchase_price: 10, rrp: 20, currency: UAH, availability: in_stock}}\n'
            )


def write_xlsx(path, rows):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns:r="urn:rel"><sheets><sheet name="Sheet1" r:id="sheet"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="sheet" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        with archive.open("xl/sharedStrings.xml", "w", force_zip64=True) as out:
            out.write(b"<sst>")
            for value in (
                "external_id",
                "sku",
                "title",
                "purchase_price",
                "rrp",
                "currency",
                "availability",
            ):
                out.write(f"<si><t>{value}</t></si>".encode())
            for i in range(rows):
                out.write(f"<si><t>Offer {i}</t></si>".encode())
            out.write(b"</sst>")
        with archive.open("xl/worksheets/sheet1.xml", "w", force_zip64=True) as out:
            out.write(b'<worksheet><sheetData><row r="1">')
            for i, letter in enumerate("ABCDEFG"):
                out.write(f'<c r="{letter}1" t="s"><v>{i}</v></c>'.encode())
            out.write(b"</row>")
            for i in range(rows):
                r = i + 2
                out.write(
                    f'<row r="{r}"><c r="A{r}"><v>{i}</v></c><c r="B{r}" t="inlineStr"><is><t>SKU-{i}</t></is></c><c r="C{r}" t="s"><v>{i+7}</v></c><c r="D{r}"><v>10</v></c><c r="E{r}"><v>20</v></c><c r="F{r}" t="inlineStr"><is><t>UAH</t></is></c><c r="G{r}" t="inlineStr"><is><t>in_stock</t></is></c></row>'.encode()
                )
            out.write(b"</sheetData></worksheet>")


class LocalSource:
    """Benchmark isolates parser/DB throughput from partner network variance."""

    def __init__(self, path):
        self.path = path

    @asynccontextmanager
    async def open(self, url):
        with self.path.open("rb") as source:
            checksum = await asyncio.to_thread(
                lambda: hashlib.file_digest(source, "sha256").hexdigest()
            )
        yield FetchResult(
            self.path, checksum, "application/octet-stream", self.path.stat().st_size
        )


class Observer:
    def __init__(self, name):
        self.name = name
        self.phases = {}
        self.result = {}

    def batch(self, phase, source_format, rows):
        """Keeps batch instrumentation equivalent to the production adapter."""
        pass

    def phase(self, name, source_format, seconds):
        self.phases[name] = round(seconds, 3)
        print(
            json.dumps(
                dict(
                    event="phase", job=self.name, phase=name, seconds=round(seconds, 3)
                )
            ),
            flush=True,
        )

    def completed(self, source_format, trigger, status, counters, seconds):
        self.result = dict(
            format=source_format,
            status=status,
            counters=counters,
            duration_seconds=round(seconds, 3),
            phases=self.phases,
        )
        print(
            json.dumps(dict(event="completed", job=self.name, **self.result)),
            flush=True,
        )

    def downloaded(self, source_format, size):
        self.phases["source_bytes"] = size


async def execute_group(specifications, heartbeat_path):
    """Runs the production worker, including claim, lease heartbeat and completion."""
    handlers = {}
    observers = []
    counts = []
    listeners = []
    commands = []
    for case, path, label in specifications:
        command = replace(await case.job(), trigger="cron")
        use_case = case.use_case([], parser=SourceParser(case.options))
        use_case.fetcher = LocalSource(path)
        observer = Observer(label)
        use_case.observer = observer
        observers.append(observer)
        handlers[command.job_id.uuid] = PriceListSyncJobHandler(use_case)
        commands.append(command)
        counter = [0]
        counts.append(counter)

        def queried(*args, counter=counter):
            counter[0] += 1

        listeners.append((case.engine.sync_engine, queried))
        event.listen(case.engine.sync_engine, "before_cursor_execute", queried)
        async with case.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == command.job_id.uuid)
                .values(
                    status="scheduled",
                    attempts=0,
                    lock_token=None,
                    locked_until=None,
                    payload=dict(
                        price_list_id=str(command.price_list_id),
                        schedule_revision=command.revision,
                        trigger="cron",
                        planned_at=command.planned_at.isoformat(),
                    ),
                )
            )
            await session.commit()

    class Dispatcher:
        async def dispatch(self, job):
            await handlers[job.id].handle(job)

    worker = ScheduledJobWorker(
        session_factory=specifications[0][0].sessions,
        dispatcher=Dispatcher(),
        process_limit=4,
        recover_limit=4,
        lock_ttl_seconds=30,
        lock_heartbeat_seconds=5,
        retry_base_seconds=60,
        max_attempts=3,
        poll_interval_seconds=1,
        recover_interval_seconds=10,
        heartbeat_path=heartbeat_path,
        concurrency=4,
        job_timeout_seconds=3600,
    )
    try:
        assert await worker.process_once() == len(specifications)
        async with specifications[0][0].sessions() as session:
            states = (
                (
                    await session.execute(
                        select(ScheduledJobModel.status).where(
                            ScheduledJobModel.id.in_([c.job_id.uuid for c in commands])
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert states == ["done"] * len(commands), states
    finally:
        for engine, listener in listeners:
            event.remove(engine, "before_cursor_execute", listener)
    results = []
    for (case, _, _), observer, counter in zip(
        specifications, observers, counts, strict=True
    ):
        results.append(
            observer.result
            | dict(
                sql_statements=counter[0],
                offers=await case.count(PartnerOfferModel),
                states=await case.count(PartnerOfferStateModel),
            )
        )
    return results


async def execute(case, path, label):
    return (
        await execute_group([(case, path, label)], path.parent / "worker.heartbeat")
    )[0]


async def benchmark(args):
    cases = []
    started = time.monotonic()
    report = dict(rows=args.rows, concurrency=4, results={})
    with tempfile.TemporaryDirectory(
        prefix="dnk-price-benchmark-", dir=args.temp_dir
    ) as directory:
        directory = Path(directory)
        paths = {fmt: directory / f"feed.{fmt}" for fmt in ("xml", "yaml", "xlsx")}
        for fmt, writer in (
            ("xml", write_xml),
            ("yaml", write_yaml),
            ("xlsx", write_xlsx),
        ):
            print(
                json.dumps(dict(event="generate", format=fmt, rows=args.rows)),
                flush=True,
            )
            await asyncio.to_thread(writer, paths[fmt], args.rows)
        report["fixture_bytes"] = {fmt: p.stat().st_size for fmt, p in paths.items()}
        disk_peak = [sum(report["fixture_bytes"].values())]

        async def sample_disk():
            while True:
                sizes = await asyncio.to_thread(
                    lambda: sum(
                        p.stat().st_size for p in directory.rglob("*") if p.is_file()
                    )
                )
                disk_peak[0] = max(disk_peak[0], sizes)
                await asyncio.sleep(0.5)

        sampler = asyncio.create_task(sample_disk())
        try:
            for fmt in ("xml", "yaml", "xlsx", "xml"):
                case = PriceListBulkPostgresTests(
                    "test_large_import_and_equivalent_repeat_have_bounded_queries"
                )
                await case.asyncSetUp()
                cases.append(case)
                async with case.engine.begin() as connection:
                    await connection.run_sync(
                        lambda conn: TenantModel.__table__.create(conn, checkfirst=True)
                    )
                    await connection.execute(
                        insert(TenantModel).values(
                            id=case.tenant_id.uuid,
                            name="Benchmark",
                            external_id="benchmark-" + str(case.tenant_id),
                            status="active",
                        )
                    )
                if fmt != "xml":
                    async with case.transactions() as tx:
                        price = await tx.prices.get(case.tenant_id, case.price_id)
                        mapping = {
                            key: {"selector": key}
                            for key in (
                                "external_id",
                                "sku",
                                "title",
                                "purchase_price",
                                "rrp",
                                "currency",
                                "availability",
                            )
                        }
                        price.update(
                            dict(
                                source_format=fmt,
                                source_config=(
                                    {"item_path": "offers"}
                                    if fmt == "yaml"
                                    else {"sheet_name": "Sheet1", "header_row": 1}
                                ),
                                mapping_config=mapping,
                            ),
                            case.actor_id,
                            datetime.now(UTC),
                        )
                        await tx.prices.save(case.tenant_id, price)
            async with cases[0].engine.connect() as connection:
                before = await connection.scalar(
                    text("SELECT pg_current_wal_lsn()::text")
                )
            results = await execute_group(
                [
                    (case, paths[fmt], f"initial-{index}-{fmt}")
                    for index, (case, fmt) in enumerate(
                        zip(cases, ("xml", "yaml", "xlsx", "xml"), strict=True)
                    )
                ],
                directory / "worker.heartbeat",
            )
            report["results"]["parallel_initial"] = results
            assert all(
                r["offers"] == args.rows and r["states"] == args.rows for r in results
            )
            if not args.initial_only:
                case = cases[0]
                repeat = await execute(case, paths["xml"], "unchanged")
                report["results"]["unchanged"] = repeat
                assert (
                    repeat["states"] == args.rows and repeat["counters"]["changed"] == 0
                )
                await asyncio.to_thread(
                    write_xml, paths["xml"], args.rows, changed=True
                )
                changed = await execute(case, paths["xml"], "one_percent_changed")
                report["results"]["changed"] = changed
                assert changed["counters"]["changed"] == (args.rows + 99) // 100
                async with case.transactions() as tx:
                    price = await tx.prices.get(case.tenant_id, case.price_id)
                    price.update(
                        dict(missing_threshold=1), case.actor_id, datetime.now(UTC)
                    )
                    await tx.prices.save(case.tenant_id, price)
                await asyncio.to_thread(write_xml, paths["xml"], 10, changed=True)
                missing = await execute(case, paths["xml"], "mass_missing")
                report["results"]["missing"] = missing
                assert missing["counters"]["missing"] == args.rows - 10
            async with cases[0].engine.connect() as connection:
                report["wal_bytes"] = int(
                    await connection.scalar(
                        text(
                            "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(),CAST(CAST(:before AS text) AS pg_lsn))"
                        ),
                        dict(before=str(before)),
                    )
                )
                schema = cases[0].schema
                report["query_plan"] = await connection.scalar(
                    text(
                        f'EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT o.id,s.purchase_price FROM "{schema}".partner_offers o JOIN "{schema}".partner_offer_states s ON s.id=o.current_state_id ORDER BY s.observed_at DESC NULLS LAST,o.id LIMIT 50'
                    )
                )
        finally:
            sampler.cancel()
            await asyncio.gather(sampler, return_exceptions=True)
            report["peak_temp_bytes"] = disk_peak[0]
            for case in cases:
                async with case.engine.begin() as connection:
                    await connection.execute(
                        delete(TenantModel).where(TenantModel.id == case.tenant_id.uuid)
                    )
                await case.asyncTearDown()
    report["sql_statement_scope"] = (
        "SQLAlchemy statements; native COPY RPCs are additional bounded batch calls."
    )
    report["duration_seconds"] = round(time.monotonic() - started, 3)
    report["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    for name in ("memory.peak", "memory.max"):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            report[name] = path.read_text().strip()
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(
        json.dumps(
            dict(
                event="report",
                output=str(args.output),
                peak_rss_bytes=report["peak_rss_bytes"],
                duration_seconds=report["duration_seconds"],
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1_000_001)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-dir", default="/tmp")
    parser.add_argument("--initial-only", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("TEST_POSTGRES_URL"):
        parser.error("TEST_POSTGRES_URL must target disposable PostgreSQL")
    if not 10 <= args.rows <= 1048575:
        parser.error("rows must fit one XLSX worksheet including header")
    asyncio.run(benchmark(args))
