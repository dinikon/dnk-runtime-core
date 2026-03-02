from contextlib import asynccontextmanager
from src.common.db.helper import db_helper

# from src.middleware import apply_middleware
# from src.router import apply_routes

from src.dnk_app import DnkApp


@asynccontextmanager
async def lifespan(app: DnkApp):
    app.state.db = db_helper.session_factory
    app.state.db_helper = db_helper
    await db_helper.create_all()
    yield
    await db_helper.dispose()


def create_app() -> DnkApp:
    app = DnkApp(lifespan=lifespan)
    # apply_routes(app)
    return app
