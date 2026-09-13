import asyncio
import json
import os
from pathlib import Path
import subprocess
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

root = Path(os.environ["DNK_HTTPS_FIXTURE_DIRECTORY"])
repo = Path(os.environ["DNK_RUNTIME_REPOSITORY"])
env = dict(os.environ, **json.loads((root / "environment.json").read_text()))
env["PYTHONPATH"] = str(root) + ":" + str(repo)


async def create():
    engine = create_async_engine(
        os.environ["DNK_TEST_DATABASE_URL"].replace(
            "postgresql://", "postgresql+asyncpg://", 1
        ),
        isolation_level="AUTOCOMMIT",
    )
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text('CREATE DATABASE "' + os.environ["DNK_HTTPS_DATABASE_NAME"] + '"')
            )
    finally:
        await engine.dispose()


asyncio.run(create())
(root / "database-created").touch()
subprocess.run(
    [str(repo / ".venv/bin/python"), "-m", "src.management.cli", "database", "upgrade"],
    cwd=repo,
    env=env,
    check=True,
)
pids = {}
for label, args in [
    (
        "api",
        [
            "-m",
            "uvicorn",
            "src.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            os.environ["DNK_HTTPS_API_PORT"],
            "--no-proxy-headers",
        ],
    ),
    ("worker", ["-m", "src.modules.control_plane.worker"]),
]:
    output = (root / (label + ".log")).open("wb")
    process = subprocess.Popen(
        [str(repo / ".venv/bin/python"), *args],
        cwd=repo,
        env=env,
        stdout=output,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pids[label] = process.pid
(root / "pids.json").write_text(json.dumps(pids))
print("Started task-owned Runtime API and worker:", pids)
