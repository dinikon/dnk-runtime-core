"""Opt-in HTTPS peer for the sibling Control Plane deletion integration test.

Runs production HTTP handlers, SQL migrations/workers and Redis cleanup on
explicitly supplied disposable stores. TLS itself verifies the test client CA;
the small middleware models the authenticated ingress-to-ASGI handoff.
"""

import asyncio
from contextlib import asynccontextmanager, suppress
import json
import os
from pathlib import Path
import socket
import ssl
import sys
from unittest.mock import patch

from fastapi import FastAPI, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import uvicorn

from test.test_control_plane_runtime import configuration
from src.modules.control_plane.infrastructure.deletion import DeletionWorker
from src.modules.control_plane.infrastructure.worker_engine import (
    Installer,
    due_attempts,
)
from src.modules.control_plane.presentation.router import router
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.tokens.redis_token_repository import (
    RedisTokenRepository,
)
from src.modules.shared.presentation.http.tenant_gate import TenantAdmissionMiddleware


async def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    engine = create_async_engine(os.environ["TEST_CP_POSTGRES_URL"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    settings = configuration().model_copy(
        update={
            "enabled": True,
            "public_origin": "https://testserver",
            "allowed_base_domains": ["tenant.test"],
        }
    )
    installer = Installer(sessions, settings, "dnk_")
    deletion = DeletionWorker(sessions, settings, "dnk_")

    async def work():
        while True:
            async with sessions() as session:
                attempts = await due_attempts(session)
            for attempt in attempts:
                await installer.run(attempt)
            await deletion.due()
            await asyncio.sleep(0.05)

    @asynccontextmanager
    async def lifespan(app):
        async with engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
        worker = asyncio.create_task(work())
        try:
            yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.db, app.state.control_plane_settings = sessions, settings
    app.include_router(router)
    app.add_middleware(TenantAdmissionMiddleware)

    @app.middleware("http")
    async def verified_tls_ingress(request: Request, call_next):
        request.state.control_plane_trusted = True
        return await call_next(request)

    @app.get("/probe")
    async def probe():
        return {"business_data": True}

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    print(listener.getsockname()[1], flush=True)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            access_log=False,
            log_level="error",
            ssl_certfile=config["server_cert"],
            ssl_keyfile=config["server_key"],
            ssl_ca_certs=config["ca"],
            ssl_cert_reqs=ssl.CERT_REQUIRED,
        )
    )
    with patch.object(
        RedisTokenRepository,
        "from_config",
        side_effect=lambda: RedisTokenRepository(
            Redis.from_url(os.environ["TEST_DELETION_REDIS_URL"])
        ),
    ):
        await server.serve(sockets=[listener])


if __name__ == "__main__":
    asyncio.run(main())
