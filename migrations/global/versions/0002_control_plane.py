"""Immutable PostgreSQL integration tables."""

from alembic import op

revision = "0002_control_plane"
down_revision = "0001_runtime_public"
branch_labels = None
depends_on = None

DDL = (
    "CREATE TABLE cp_access_projections (\n\tcore_tenant_id UUID NOT NULL, \n\tglobal_user_id UUID NOT NULL, \n\tavailable BOOLEAN NOT NULL, \n\tversion BIGINT NOT NULL, \n\tPRIMARY KEY (core_tenant_id, global_user_id), \n\tCHECK (version >= 1)\n)",
    "CREATE TABLE cp_cloud_connections (\n\truntime_tenant_id UUID NOT NULL, \n\tcore_tenant_id UUID NOT NULL, \n\tissuer VARCHAR(2048) NOT NULL, \n\tclient_id VARCHAR(255) NOT NULL, \n\tcallback VARCHAR(2048) NOT NULL, \n\tencrypted_secret TEXT NOT NULL, \n\tPRIMARY KEY (runtime_tenant_id), \n\tUNIQUE (core_tenant_id)\n)",
    "CREATE TABLE cp_delivery_outbox (\n\tevent_id UUID NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\taggregate_id UUID NOT NULL, \n\tcore_tenant_id UUID NOT NULL, \n\tversion BIGINT NOT NULL, \n\tpayload JSONB NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tattempts BIGINT NOT NULL, \n\tfencing_token BIGINT NOT NULL, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tnext_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\terror_code VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdelivered_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (event_id), \n\tCHECK (kind IN ('install','access')), \n\tCHECK (state IN ('pending','running','delivered','blocked')), \n\tCONSTRAINT cp_delivery_version_uq UNIQUE (kind, core_tenant_id, aggregate_id, version)\n)",
    "CREATE INDEX cp_delivery_due_idx ON cp_delivery_outbox (state, next_attempt_at, lease_until)",
    "CREATE TABLE cp_installations (\n\tcore_tenant_id UUID NOT NULL, \n\truntime_tenant_id UUID NOT NULL, \n\thostname VARCHAR(253) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tcurrent_attempt_id UUID NOT NULL, \n\towner_user_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (core_tenant_id), \n\tUNIQUE (runtime_tenant_id), \n\tUNIQUE (hostname)\n)",
    "CREATE TABLE cp_provisioning_attempts (\n\tattempt_id UUID NOT NULL, \n\toperation_id UUID NOT NULL, \n\tcore_tenant_id UUID NOT NULL, \n\tcommand_hash VARCHAR(64) NOT NULL, \n\tencrypted_command TEXT NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tresources_state VARCHAR(16) NOT NULL, \n\tstep VARCHAR(32) NOT NULL, \n\tstep_duration_ms BIGINT DEFAULT '0' NOT NULL, \n\tfencing_token BIGINT NOT NULL, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tnext_attempt_at TIMESTAMP WITH TIME ZONE, \n\terror_code VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (attempt_id), \n\tCHECK (state IN ('queued','running','succeeded','failed')), \n\tCHECK (resources_state IN ('absent','present','unknown'))\n)",
    "CREATE INDEX cp_attempt_recovery_idx ON cp_provisioning_attempts (state, lease_until, next_attempt_at)",
    "CREATE INDEX ix_cp_provisioning_attempts_core_tenant_id ON cp_provisioning_attempts (core_tenant_id)",
    "CREATE TABLE cp_readiness_observations (\n\tkey VARCHAR(253) NOT NULL, \n\trouting_ready BOOLEAN NOT NULL, \n\ttls_ready BOOLEAN NOT NULL, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (key)\n)",
)


def upgrade():
    for statement in DDL:
        op.execute(statement)


def downgrade():
    raise RuntimeError(
        "Public schema downgrade is intentionally unsupported; preserve tenant data."
    )
