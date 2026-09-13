"""Real Core RuntimeClient -> nginx mTLS -> Runtime/PostgreSQL/RabbitMQ smoke.

The three DNK_TEST_*_URL environment variables point to disposable local test
services. This creates and removes only its own database, queues and container.
Run with the Runtime virtualenv; the sibling Core virtualenv supplies Django.
"""

import argparse
import asyncio
import ipaddress
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


async def clean_database_and_queues(root, env):
    if (root / "database-created").exists():
        url = make_url(env["DNK_TEST_DATABASE_URL"]).set(
            drivername="postgresql+asyncpg"
        )
        engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as connection:
                await connection.execute(
                    text(
                        'DROP DATABASE "'
                        + env["DNK_HTTPS_DATABASE_NAME"]
                        + '" WITH (FORCE)'
                    )
                )
        finally:
            await engine.dispose()
    if (root / "environment.json").exists():
        import aio_pika

        settings = json.loads((root / "environment.json").read_text())
        broker = await aio_pika.connect_robust(env["DNK_TEST_RABBITMQ_URL"])
        try:
            channel = await broker.channel()
            for key in ("CONTROL_PLANE__INSTALL_QUEUE", "CONTROL_PLANE__ACCESS_QUEUE"):
                try:
                    await channel.queue_delete(
                        settings[key], if_unused=False, if_empty=False
                    )
                except Exception:
                    # Closing a failed channel does not affect other test queues.
                    channel = await broker.channel()
        finally:
            await broker.close()


def main():
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--core-repository", type=Path, default=repo.parent / "dnk-control-plane"
    )
    parser.add_argument("--nginx-image", default="nginx:1.27-alpine")
    parser.add_argument(
        "--output", type=Path, help="Write non-secret JSON verification results here"
    )
    args = parser.parse_args()
    required = ("DNK_TEST_DATABASE_URL", "DNK_TEST_RABBITMQ_URL", "DNK_TEST_REDIS_URL")
    if any(not os.environ.get(key) for key in required):
        parser.error(
            "Set DNK_TEST_DATABASE_URL, DNK_TEST_RABBITMQ_URL and DNK_TEST_REDIS_URL to isolated test services"
        )
    core_python = args.core_repository / ".venv/bin/python"
    if (
        not core_python.exists()
        or not (args.core_repository / "src/operations/runtime.py").exists()
    ):
        parser.error("Core checkout and its installed .venv are required")
    suffix = uuid4().hex[:12]
    root = Path(tempfile.mkdtemp(prefix="dnk-runtime-https-"))
    container = "dnk-runtime-https-" + suffix
    fixture = Path(__file__).parent / "https_fixture"
    env = dict(
        os.environ,
        DNK_HTTPS_FIXTURE_DIRECTORY=str(root),
        DNK_RUNTIME_REPOSITORY=str(repo),
        DNK_CORE_REPOSITORY=str(args.core_repository),
        DNK_HTTPS_DATABASE_NAME="dnk_https_" + suffix,
        DNK_HTTPS_PORT=str(free_port()),
        DNK_HTTPS_API_PORT=str(free_port()),
        DNK_HTTPS_TRUSTED_PEERS='["127.0.0.1/32"]',
    )
    env["PYTHONPATH"] = str(root) + os.pathsep + str(repo)
    # Per-process DNS/port mapping exercises actual TLS SNI without editing hosts
    # or claiming privileged port 443. No business/API transport is mocked.
    (root / "sitecustomize.py").write_text("""import os, socket
_original = socket.getaddrinfo
def _fixture(host, port, *args, **kwargs):
    if isinstance(host, bytes): host = host.decode("ascii")
    if isinstance(host, str) and host.endswith(".example.test"):
        host = "127.0.0.1"
        if str(port) == "443": port = int(os.environ["DNK_HTTPS_PORT"])
    return _original(host, port, *args, **kwargs)
socket.getaddrinfo = _fixture
""")

    def run(script, python=sys.executable):
        subprocess.run(
            [str(python), str(fixture / script)], cwd=repo, env=env, check=True
        )

    try:
        run("prepare.py")
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--pull=never",
                "--name",
                container,
                "--add-host=host.docker.internal:host-gateway",
                "-p",
                "127.0.0.1:" + env["DNK_HTTPS_PORT"] + ":443",
                "--mount",
                "type=bind,source=" + str(root) + ",target=/fixture,readonly",
                args.nginx_image,
                "nginx",
                "-c",
                "/fixture/nginx.conf",
                "-g",
                "daemon off;",
            ],
            check=True,
            capture_output=True,
        )
        network = json.loads(
            subprocess.check_output(["docker", "inspect", container], text=True)
        )[0]["NetworkSettings"]["Networks"]
        peers = ["127.0.0.1/32"]
        for item in network.values():
            address = item.get("IPAddress")
            if address:
                peers.append(str(ipaddress.ip_address(address)) + "/32")
        settings = json.loads((root / "environment.json").read_text())
        settings["CONTROL_PLANE__TRUSTED_PROXY_NETWORKS"] = json.dumps(peers)
        (root / "environment.json").write_text(json.dumps(settings))
        run("start.py")
        run("verify.py", core_python)
        run("recovery.py", core_python)
        result = {
            "https": json.loads((root / "verification.json").read_text()),
            "recovery": json.loads((root / "recovery-verification.json").read_text()),
            "network_policy": "Manifest tested; no Kubernetes CNI in this local harness",
        }
        if args.output:
            args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(
            "PASS: actual Core client, two TLS zones, mTLS rejection/rotation, duplicate commands and durable worker recovery"
        )
    finally:
        if (root / "pids.json").exists():
            for pid in json.loads((root / "pids.json").read_text()).values():
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        subprocess.run(["docker", "rm", "--force", container], capture_output=True)
        try:
            asyncio.run(clean_database_and_queues(root, env))
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    main()
