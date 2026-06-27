from contextlib import asynccontextmanager

from src.config import dnk_config
from src.dnk_app import DnkApp
from src.modules.communication.infrastructure.rabbitmq import (
    RabbitMQOutboundMessagePublisher,
    ensure_communication_topology,
)
from src.modules.router import router as api_router
from src.modules.shared.infrastructure.events import ensure_event_bus_topology
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerProvider,
    RabbitMQBrokerPublisher,
    RabbitMQTopologyManager,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper


@asynccontextmanager
async def lifespan(app: DnkApp):
    app.state.db = db_helper.session_factory
    app.state.db_helper = db_helper
    rabbitmq_provider = None
    broker_publisher = None
    communication_publisher = None
    try:
        await db_helper.initialize_for_startup()
        if dnk_config.RABBITMQ.enabled:
            rabbitmq_provider = RabbitMQBrokerProvider(dnk_config.RABBITMQ)
            await rabbitmq_provider.start()

            broker_publisher = RabbitMQBrokerPublisher(rabbitmq_provider)
            topology = RabbitMQTopologyManager(rabbitmq_provider)

            if dnk_config.COMMUNICATION_QUEUE.enabled:
                await ensure_communication_topology(
                    topology,
                    dnk_config.COMMUNICATION_QUEUE,
                )
                communication_publisher = RabbitMQOutboundMessagePublisher(
                    broker_publisher=broker_publisher,
                    settings=dnk_config.COMMUNICATION_QUEUE,
                )

            await ensure_event_bus_topology(
                topology,
                dnk_config.EVENT_BUS,
            )

            app.state.rabbitmq_provider = rabbitmq_provider
            app.state.broker_publisher = broker_publisher
            app.state.broker_topology = topology
            app.state.communication_outbound_publisher = communication_publisher
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
    app = DnkApp(
        lifespan=lifespan,
        title="DNK API",
        version="1.0.0",
        description="DNK API is a RESTful API for managing digital knowledge.",
        servers=[
            {"url": "http://localhost:8000", "description": "Default Develop Server"},
            {"url": "https://test.dniko.app", "description": "Test Server"},
            {"url": "https://dniko.app", "description": "Production Server"},
        ],
    )
    app.include_router(api_router)
    return app
