from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the minimal Control Plane API application."""

    app = FastAPI(
        title="DNK Control Plane API",
        version="0.1.0",
        description="Global management plane for DNK installations and tenants.",
    )

    @app.get("/health/live", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness() -> dict[str, str]:
        # Database, Redis and broker checks are added with backend foundation.
        return {"status": "ready"}

    return app


__all__ = ["create_app"]
