from contextlib import asynccontextmanager
import asyncio

from fastapi.responses import JSONResponse

from src.config import dnk_config
from src.dnk_app import DnkApp
from src.modules.router import router as api_router
from src.modules.control_plane.presentation.router import router as control_plane_router
from src.modules.identity.presentation.http.integration import (
    router as identity_integration_router,
    cloud_router,
)
from src.modules.shared.infrastructure.events import ensure_event_bus_topology
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerProvider,
    RabbitMQBrokerPublisher,
    RabbitMQTopologyManager,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.presentation.http.trust_boundary import (
    ManagementTrustBoundary,
    install_access_log_redaction,
)


@asynccontextmanager
async def lifespan(app: DnkApp):
    app.state.db = db_helper.session_factory
    app.state.db_helper = db_helper
    rabbitmq_provider = None
    broker_publisher = None
    try:
        await db_helper.initialize_for_startup()
        if dnk_config.RABBITMQ.enabled:
            rabbitmq_provider = RabbitMQBrokerProvider(dnk_config.RABBITMQ)
            await rabbitmq_provider.start()

            broker_publisher = RabbitMQBrokerPublisher(rabbitmq_provider)
            topology = RabbitMQTopologyManager(rabbitmq_provider)

            await ensure_event_bus_topology(
                topology,
                dnk_config.EVENT_BUS,
            )

            app.state.rabbitmq_provider = rabbitmq_provider
            app.state.broker_publisher = broker_publisher
            app.state.broker_topology = topology
    except Exception:
        if rabbitmq_provider is not None:
            await rabbitmq_provider.close()
        await db_helper.dispose()
        raise

    try:
        yield
    finally:
        if rabbitmq_provider is not None:
            await rabbitmq_provider.close()
        await db_helper.dispose()


def create_app() -> DnkApp:
    install_access_log_redaction()
    app = DnkApp(
        lifespan=lifespan,
        title="DNK API",
        version=dnk_config.project.version or "0.0.0",
        description="DNK API is a RESTful API for managing digital knowledge.",
        servers=[
            {"url": "http://localhost:8000", "description": "Default Develop Server"},
            {"url": "https://test.dniko.app", "description": "Test Server"},
            {"url": "https://dniko.app", "description": "Production Server"},
        ],
    )
    app.include_router(api_router)
    app.include_router(control_plane_router)
    app.include_router(identity_integration_router)
    app.include_router(cloud_router)
    integration = dnk_config.CONTROL_PLANE
    app.add_middleware(
        ManagementTrustBoundary,
        enabled=integration.enabled,
        management_host=integration.management_host,
        trusted_proxy_networks=integration.trusted_proxy_networks,
        allowed_core_fingerprints=integration.allowed_core_fingerprints,
    )

    @app.get("/health/live", include_in_schema=False)
    async def live():
        return {"live": True}

    @app.get("/health/ready", include_in_schema=False)
    async def ready():
        try:
            async with asyncio.timeout(2):
                async with db_helper.engine.connect() as connection:
                    await GlobalMigrator().require_current(connection)
            return {"ready": True}
        except Exception:
            return JSONResponse({"ready": False}, status_code=503)

    return app
