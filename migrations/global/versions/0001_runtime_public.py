"""Immutable PostgreSQL fresh-database public baseline."""

from alembic import op

revision = "0001_runtime_public"
down_revision = None
branch_labels = None
depends_on = None

DDL = (
    "CREATE TABLE integration_inbox_events (\n\tid UUID NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tsource VARCHAR(255) NOT NULL, \n\tmessage_id VARCHAR(255) NOT NULL, \n\tevent_type VARCHAR(255) NOT NULL, \n\tconsumed_at TIMESTAMP WITH TIME ZONE, \n\tstatus VARCHAR(50) DEFAULT 'received' NOT NULL, \n\terror TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT integration_inbox_message_uq UNIQUE (tenant_id, source, message_id)\n)",
    "CREATE INDEX integration_inbox_event_type_idx ON integration_inbox_events (event_type)",
    "CREATE INDEX ix_integration_inbox_events_status ON integration_inbox_events (status)",
    "CREATE INDEX ix_integration_inbox_events_tenant_id ON integration_inbox_events (tenant_id)",
    "CREATE TABLE integration_outbox_events (\n\tid UUID NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tevent_type VARCHAR(255) NOT NULL, \n\tevent_version INTEGER NOT NULL, \n\taggregate_type VARCHAR(255) NOT NULL, \n\taggregate_id UUID NOT NULL, \n\tpayload JSONB NOT NULL, \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tpublished_at TIMESTAMP WITH TIME ZONE, \n\tpublish_attempts INTEGER DEFAULT 0 NOT NULL, \n\tstatus VARCHAR(50) DEFAULT 'pending' NOT NULL, \n\tnext_attempt_at TIMESTAMP WITH TIME ZONE, \n\tlast_error TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id)\n)",
    "CREATE INDEX integration_outbox_aggregate_idx ON integration_outbox_events (tenant_id, aggregate_type, aggregate_id)",
    "CREATE INDEX integration_outbox_due_idx ON integration_outbox_events (status, next_attempt_at, occurred_at)",
    "CREATE INDEX ix_integration_outbox_events_event_type ON integration_outbox_events (event_type)",
    "CREATE INDEX ix_integration_outbox_events_next_attempt_at ON integration_outbox_events (next_attempt_at)",
    "CREATE INDEX ix_integration_outbox_events_status ON integration_outbox_events (status)",
    "CREATE INDEX ix_integration_outbox_events_tenant_id ON integration_outbox_events (tenant_id)",
    "CREATE TABLE scheduled_jobs (\n\tid UUID NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tjob_type VARCHAR(255) NOT NULL, \n\tpayload JSONB NOT NULL, \n\trun_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(50) DEFAULT 'scheduled' NOT NULL, \n\tattempts INTEGER DEFAULT 0 NOT NULL, \n\tlocked_until TIMESTAMP WITH TIME ZONE, \n\tlock_token VARCHAR(255), \n\tlast_error TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id)\n)",
    "CREATE INDEX ix_scheduled_jobs_job_type ON scheduled_jobs (job_type)",
    "CREATE INDEX ix_scheduled_jobs_locked_until ON scheduled_jobs (locked_until)",
    "CREATE INDEX ix_scheduled_jobs_run_at ON scheduled_jobs (run_at)",
    "CREATE INDEX ix_scheduled_jobs_status ON scheduled_jobs (status)",
    "CREATE INDEX ix_scheduled_jobs_tenant_id ON scheduled_jobs (tenant_id)",
    "CREATE INDEX scheduled_jobs_due_idx ON scheduled_jobs (status, run_at)",
    "CREATE INDEX scheduled_jobs_stuck_idx ON scheduled_jobs (status, locked_until)",
    "CREATE INDEX scheduled_jobs_tenant_type_idx ON scheduled_jobs (tenant_id, job_type)",
    "CREATE TABLE tenants (\n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\texternal_id VARCHAR(255) NOT NULL, \n\tstatus VARCHAR(255) DEFAULT 'active' NOT NULL, \n\tcustom_config JSONB, \n\tPRIMARY KEY (id)\n)",
    "CREATE UNIQUE INDEX ix_tenants_external_id ON tenants (external_id)",
    "CREATE INDEX ix_tenants_status ON tenants (status)",
    "CREATE TABLE tenant_domains (\n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tservice_type VARCHAR(32) NOT NULL, \n\tkind VARCHAR(32) NOT NULL, \n\thost VARCHAR(255) NOT NULL, \n\tbase_path VARCHAR(255), \n\tauth_mode VARCHAR(32), \n\tstatus VARCHAR(32) DEFAULT 'active' NOT NULL, \n\tis_primary BOOLEAN NOT NULL, \n\tis_wildcard BOOLEAN NOT NULL, \n\tparent_domain VARCHAR(255), \n\tverification_status VARCHAR(32) DEFAULT 'verified' NOT NULL, \n\ttls_mode VARCHAR(32) DEFAULT 'managed' NOT NULL, \n\tmetadata_json JSONB, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_saas_tenant_service_domain UNIQUE (tenant_id, service_type, host, base_path), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id)\n)",
    "CREATE UNIQUE INDEX ix_tenant_domains_host ON tenant_domains (host)",
    "CREATE INDEX ix_tenant_domains_is_primary ON tenant_domains (is_primary)",
    "CREATE INDEX ix_tenant_domains_kind ON tenant_domains (kind)",
    "CREATE INDEX ix_tenant_domains_service_type ON tenant_domains (service_type)",
    "CREATE INDEX ix_tenant_domains_status ON tenant_domains (status)",
    "CREATE INDEX ix_tenant_domains_tenant_id ON tenant_domains (tenant_id)",
)


def upgrade():
    for statement in DDL:
        op.execute(statement)


def downgrade():
    raise RuntimeError(
        "Public schema downgrade is intentionally unsupported; preserve tenant data."
    )
