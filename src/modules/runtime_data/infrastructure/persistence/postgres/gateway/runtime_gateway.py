from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.application.ports import RuntimeRelationLoader
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler import (
    PostgresRuntimeQueryCompiler,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.execution import (
    PostgresSqlExecutor,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.relation_loader import (
    PostgresRuntimeRelationLoader,
)


class PostgresRuntimeGateway(
    PostgresRuntimeCommandGateway,
    PostgresRuntimeQueryGateway,
):
    """Compatibility façade exposing command and query runtime gateways."""

    def __init__(
        self,
        session: AsyncSession,
        type_policy: RuntimeFieldTypePolicy | None = None,
        query_compiler: PostgresRuntimeQueryCompiler | None = None,
        relation_loader: RuntimeRelationLoader | None = None,
        executor: PostgresSqlExecutor | None = None,
    ) -> None:
        super().__init__(
            session=session,
            type_policy=type_policy,
            query_compiler=query_compiler,
            query_gateway=self,
            executor=executor,
        )
        self._relation_loader = relation_loader or PostgresRuntimeRelationLoader(
            session=session,
        )


__all__ = ["PostgresRuntimeGateway"]
