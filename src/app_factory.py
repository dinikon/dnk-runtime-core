from contextlib import asynccontextmanager

from src.config import dnk_config
from src.dnk_app import DnkApp
from src.modules.communication.infrastructure.rabbitmq import (
    RabbitMQOutboundMessagePublisher,
)
from src.modules.router import router as api_router
from src.modules.shared.infrastructure.persistence.database_helper import db_helper


@asynccontextmanager
async def lifespan(app: DnkApp):
    app.state.db = db_helper.session_factory
    app.state.db_helper = db_helper
    communication_publisher = None
    try:
        await db_helper.initialize_for_startup()
        if dnk_config.COMMUNICATION_QUEUE.enabled:
            communication_publisher = RabbitMQOutboundMessagePublisher.from_settings(
                dnk_config.COMMUNICATION_QUEUE,
                manage_broker_lifecycle=True,
            )
            await communication_publisher.start()
            app.state.communication_outbound_publisher = communication_publisher
    except Exception:
        if communication_publisher is not None:
            await communication_publisher.close()
        await db_helper.dispose()
        raise

    try:
        yield
    finally:
        if communication_publisher is not None:
            await communication_publisher.close()
        await db_helper.dispose()


def create_app() -> DnkApp:
    app = DnkApp(lifespan=lifespan)
    app.include_router(api_router)
    return app
