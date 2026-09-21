import sqlalchemy as sa
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.presentation.depends.application import (
    build_currency_components,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence import db_helper
from src.modules.shared.infrastructure.persistence.tenant_gate import TenantGate
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


async def restore_activations(args) -> int:
    """Reconcile configured tenants without changing their currency timeline."""
    clock = UtcClock()
    try:
        async with db_helper.session_factory() as session:
            query = sa.select(TenantModel.id).where(TenantModel.status == "active")
            if args.tenant_id:
                query = query.where(TenantModel.id == args.tenant_id)
            identifiers = list((await session.execute(query)).scalars())
        gate = TenantGate(db_helper.session_factory)
        for identifier in identifiers:
            async with gate.hold(identifier):
                async with UnitOfWork(db_helper.session_factory) as uow:
                    c = build_currency_components(
                        uow.session, clock, session_factory=db_helper.session_factory
                    )
                    tenant = EntityIdVO.from_value(identifier)
                    await c.repositories.policies.lock(tenant_id=tenant)
                    try:
                        policy = await c.repositories.policies.get(tenant_id=tenant)
                    except CurrencyPolicyNotConfigured:
                        continue
                    for period in await c.repositories.periods.list_periods(
                        tenant_id=tenant
                    ):
                        await c.lifecycle.ensure(
                            tenant, period, policy, period.created_by
                        )
        print(f"Activation schedules reconciled for {len(identifiers)} tenants.")
        return 0
    finally:
        await db_helper.engine.dispose()


__all__ = ["restore_activations"]
