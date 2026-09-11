"""Contextual CLI logs, timed stages and best-effort GitHub Actions summaries."""

from contextlib import contextmanager
from contextvars import ContextVar
import html
import json
import logging
import os
from pathlib import Path
import sys
import time
from collections.abc import Iterator

logger = logging.getLogger("scripts.cicd")
logger.addHandler(logging.NullHandler())
_context = ContextVar("cicd_log_context", default={})
_depth = ContextVar("cicd_stage_depth", default=0)


class ContextFormatter(logging.Formatter):
    """Append explicit operation context without dumping arguments or environment."""

    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> str:
        context = " ".join(
            f"{key}={json.dumps(str(value), ensure_ascii=False)}"
            for key, value in _context.get().items()
        )
        message = super().format(record)
        return f"{message} | {context}" if context else message


def configure_logging(level: str = "INFO") -> None:
    """Configure only the CI/CD logger; third-party loggers keep their settings."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        ContextFormatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    )
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False


@contextmanager
def log_context(**fields: object) -> Iterator[None]:
    """Bind known, non-secret fields to logs and restore the caller's context."""
    token = _context.set(_context.get() | fields)
    try:
        yield
    finally:
        _context.reset(token)


def workflow_command(command: str, text: str = "") -> None:
    """Emit an Actions control line with escaped data only on an Actions runner."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        escaped = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::{command}::{escaped}", flush=True)


def _summary(name: str, status: str, elapsed: float) -> None:
    """Append stage results even on failure; diagnostics must not fail publication."""
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destination:
        return

    def cell(value: object) -> str:
        return html.escape(" ".join(str(value).split())).replace("|", "&#124;")

    context = ", ".join(
        f"{key}={value}" for key, value in _context.get().items() if key != "stage"
    )
    try:
        path = Path(destination)
        empty = not path.exists() or path.stat().st_size == 0
        with path.open("a", encoding="utf-8") as summary:
            if empty:
                summary.write(
                    "### CI/CD stages\n\n"
                    "| Stage | Status | Seconds | Context |\n"
                    "| --- | --- | ---: | --- |\n"
                )
            summary.write(
                f"| {cell(name)} | {status} | {elapsed:.2f} | {cell(context)} |\n"
            )
    except OSError:
        logger.warning("Could not append the job summary")


@contextmanager
def stage(name: str, **fields: object) -> Iterator[None]:
    """Report start, duration and failure without swallowing the original exception.

    Only outer stages create Actions groups, because nested groups are unsupported.
    Every stage appends a summary row, including failures and interruptions.
    """
    outer = _depth.get() == 0
    token = _depth.set(_depth.get() + 1)
    started = time.monotonic()
    status = "failed"
    with log_context(**(fields | {"stage": name})):
        if outer:
            workflow_command("group", name)
        logger.info("Started")
        try:
            yield
        except BaseException as error:
            logger.error("Failed (%s)", type(error).__name__)
            if outer:
                workflow_command("error", f"{name} failed ({type(error).__name__})")
            raise
        else:
            status = "success"
        finally:
            elapsed = time.monotonic() - started
            logger.info("Finished: status=%s duration=%.2fs", status, elapsed)
            _summary(name, status, elapsed)
            if outer:
                workflow_command("endgroup")
            _depth.reset(token)
