"""Resume role projection upgrades without coupling tenant lists to Instances."""

import asyncio
import logging
from sqlalchemy import select, update, tuple_
from src.modules.control_plane.infrastructure.models import (
    AccessProjectionModel,
    InstallationModel,
    DeletionModel,
)
from src.modules.control_plane.infrastructure.services import (
    AccessProjectionWriter,
    now,
)
from src.modules.identity.infrastructure.repository.access_repository import (
    AccessRepository,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
    TenantUnavailable,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel

log = logging.getLogger(__name__)


class RoleProjectionSync:
    def __init__(self, sessions, settings, schema_prefix):
        self.sessions, self.settings = sessions, settings
        self.naming = TenantSchemaNaming(schema_prefix)

    async def due(self):
        async with self.sessions() as session, session.begin():
            batch = list(
                (
                    await session.execute(
                        select(
                            AccessProjectionModel.core_tenant_id,
                            AccessProjectionModel.global_user_id,
                            InstallationModel.runtime_tenant_id,
                        )
                        .join(
                            InstallationModel,
                            InstallationModel.core_tenant_id
                            == AccessProjectionModel.core_tenant_id,
                        )
                        .join(
                            TenantModel,
                            TenantModel.id == InstallationModel.runtime_tenant_id,
                        )
                        .where(
                            AccessProjectionModel.role_synced.is_(False),
                            TenantModel.status.in_(["active", "freeze"]),
                            ~select(DeletionModel.core_tenant_id)
                            .where(
                                DeletionModel.core_tenant_id
                                == AccessProjectionModel.core_tenant_id
                            )
                            .exists(),
                        )
                        .order_by(
                            AccessProjectionModel.sync_attempted_at.asc().nullsfirst()
                        )
                        .limit(100)
                        .with_for_update(of=AccessProjectionModel, skip_locked=True)
                    )
                ).all()
            )
            if batch:
                await session.execute(
                    update(AccessProjectionModel)
                    .where(
                        tuple_(
                            AccessProjectionModel.core_tenant_id,
                            AccessProjectionModel.global_user_id,
                        ).in_([(c, u) for c, u, _ in batch])
                    )
                    .values(sync_attempted_at=now())
                )
        for core_id, user_id, runtime_id in batch:
            try:
                async with asyncio.timeout(self.settings.step_timeout_seconds):
                    async with TenantGate(self.sessions).hold(runtime_id):
                        async with self.sessions() as session, session.begin():
                            await AccessRepository(session, self.naming).lock(
                                runtime_id
                            )
                            installation = await session.get(InstallationModel, core_id)
                            if installation:
                                await AccessProjectionWriter(session).refresh(
                                    installation,
                                    user_id,
                                    f"{self.settings.public_origin}/oidc/tenants/{core_id}",
                                    self.naming,
                                )
            except TenantUnavailable:
                pass
            except Exception:
                log.warning(
                    "Cloud role synchronization will retry",
                    extra={"tenant_id": str(core_id)},
                )
