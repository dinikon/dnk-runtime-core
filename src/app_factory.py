from contextlib import asynccontextmanager
from src.dnk_app import DnkApp
from src.modules.router import router as api_router
from src.modules.shared.db.helper import db_helper


@asynccontextmanager
async def lifespan(app: DnkApp):
    app.state.db = db_helper.session_factory
    app.state.db_helper = db_helper
    try:
        await db_helper.initialize_for_startup()
    except Exception:
        await db_helper.dispose()
        raise

    try:
        yield
    finally:
        await db_helper.dispose()


def create_app() -> DnkApp:
    app = DnkApp(lifespan=lifespan)
    app.include_router(api_router)
    return app
