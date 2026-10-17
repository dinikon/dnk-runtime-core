"""Optional admission port for tenant-aware job and event handlers."""

from contextlib import asynccontextmanager


class TenantUnavailable(Exception):
    pass


@asynccontextmanager
async def unrestricted_admission(tenant_id):
    yield
