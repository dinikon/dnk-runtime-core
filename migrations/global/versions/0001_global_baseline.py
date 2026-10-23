"""Начальная актуальная global-схема для пересозданной базы данных."""

from alembic import op

revision = "0001_global_baseline"
down_revision = None
branch_labels = None
depends_on = None

DDL = (
    "CREATE TABLE cp_access_projections (\n\tcore_tenant_id UUID NOT NULL, \n\tglobal_user_id UUID NOT NULL, \n\tavailable BOOLEAN NOT NULL, \n\tversion BIGINT NOT NULL, \n\trole VARCHAR(16), \n\trole_synced BOOLEAN DEFAULT 'false' NOT NULL, \n\tsync_attempted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (core_tenant_id, global_user_id), \n\tCHECK (version >= 1)\n)",
    "CREATE INDEX cp_access_role_sync_idx ON cp_access_projections (sync_attempted_at) WHERE NOT role_synced",
    "CREATE TABLE cp_cloud_connections (\n\truntime_tenant_id UUID NOT NULL, \n\tcore_tenant_id UUID NOT NULL, \n\tissuer VARCHAR(2048) NOT NULL, \n\tclient_id VARCHAR(255) NOT NULL, \n\tcallback VARCHAR(2048) NOT NULL, \n\tencrypted_secret TEXT NOT NULL, \n\tPRIMARY KEY (runtime_tenant_id), \n\tUNIQUE (core_tenant_id)\n)",
    "CREATE TABLE cp_delivery_outbox (\n\tevent_id UUID NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\taggregate_id UUID NOT NULL, \n\tcore_tenant_id UUID NOT NULL, \n\tversion BIGINT NOT NULL, \n\tpayload JSONB NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tattempts BIGINT NOT NULL, \n\tfencing_token BIGINT NOT NULL, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tnext_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\terror_code VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdelivered_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (event_id), \n\tCHECK (kind IN ('install','access')), \n\tCHECK (state IN ('pending','running','delivered','blocked')), \n\tCONSTRAINT cp_delivery_version_uq UNIQUE (kind, core_tenant_id, aggregate_id, version)\n)",
    "CREATE INDEX cp_delivery_due_idx ON cp_delivery_outbox (state, next_attempt_at, lease_until)",
    "CREATE TABLE cp_installations (\n\tcore_tenant_id UUID NOT NULL, \n\truntime_tenant_id UUID NOT NULL, \n\thostname VARCHAR(253) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tcurrent_attempt_id UUID NOT NULL, \n\towner_user_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (core_tenant_id), \n\tUNIQUE (runtime_tenant_id), \n\tUNIQUE (hostname)\n)",
    "CREATE TABLE cp_provisioning_attempts (\n\tattempt_id UUID NOT NULL, \n\toperation_id UUID NOT NULL, \n\tcore_tenant_id UUID NOT NULL, \n\tcommand_hash VARCHAR(64) NOT NULL, \n\tencrypted_command TEXT NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tresources_state VARCHAR(16) NOT NULL, \n\tstep VARCHAR(32) NOT NULL, \n\tstep_duration_ms BIGINT DEFAULT '0' NOT NULL, \n\tfencing_token BIGINT NOT NULL, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tnext_attempt_at TIMESTAMP WITH TIME ZONE, \n\terror_code VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (attempt_id), \n\tCHECK (state IN ('queued','running','succeeded','failed')), \n\tCHECK (resources_state IN ('absent','present','unknown'))\n)",
    "CREATE INDEX cp_attempt_recovery_idx ON cp_provisioning_attempts (state, lease_until, next_attempt_at)",
    "CREATE INDEX ix_cp_provisioning_attempts_core_tenant_id ON cp_provisioning_attempts (core_tenant_id)",
    "CREATE TABLE cp_readiness_observations (\n\tkey VARCHAR(253) NOT NULL, \n\trouting_ready BOOLEAN NOT NULL, \n\ttls_ready BOOLEAN NOT NULL, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (key)\n)",
    "CREATE TABLE cp_tenant_deletions (\n\tcore_tenant_id UUID NOT NULL, \n\truntime_tenant_id UUID, \n\toperation_id UUID NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tversion BIGINT NOT NULL, \n\tcommand JSONB, \n\tcommand_hash VARCHAR(64) NOT NULL, \n\terror_code VARCHAR(64), \n\tcreation_succeeded BOOLEAN NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (core_tenant_id), \n\tCHECK (state IN ('deletion_pending','blocked','purging','deleted')), \n\tUNIQUE (runtime_tenant_id), \n\tUNIQUE (operation_id)\n)",
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
    "CREATE TABLE public.ref_countries (\n\tcode VARCHAR(2) NOT NULL, \n\talpha3 VARCHAR(3) NOT NULL, \n\tnumeric_code VARCHAR(3) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (code), \n\tUNIQUE (alpha3), \n\tUNIQUE (numeric_code)\n)",
    "CREATE TABLE public.ref_currencies (\n\tcode VARCHAR(3) NOT NULL, \n\tnumeric_code VARCHAR(3), \n\tname VARCHAR(255) NOT NULL, \n\tminor_units SMALLINT, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (code)\n)",
    "CREATE TABLE public.ref_sync_state (\n\tdataset VARCHAR(32) NOT NULL, \n\tsource VARCHAR(255) NOT NULL, \n\tsource_version VARCHAR(100) NOT NULL, \n\tlast_success_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trow_count INTEGER NOT NULL, \n\tPRIMARY KEY (dataset)\n)",
    "CREATE TABLE public.ref_time_zones (\n\tcode VARCHAR(128) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (code)\n)",
    "CREATE TABLE scheduled_jobs (\n\tid UUID NOT NULL, \n\ttenant_id UUID, \n\tjob_type VARCHAR(255) NOT NULL, \n\tpayload JSONB NOT NULL, \n\trun_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(50) DEFAULT 'scheduled' NOT NULL, \n\tattempts INTEGER DEFAULT 0 NOT NULL, \n\tlocked_until TIMESTAMP WITH TIME ZONE, \n\tlock_token VARCHAR(255), \n\tlast_error TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id)\n)",
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
    "CREATE TABLE public.ref_country_time_zones (\n\tcountry_code VARCHAR(2) NOT NULL, \n\ttime_zone_code VARCHAR(128) NOT NULL, \n\tPRIMARY KEY (country_code, time_zone_code), \n\tFOREIGN KEY(country_code) REFERENCES public.ref_countries (code), \n\tFOREIGN KEY(time_zone_code) REFERENCES public.ref_time_zones (code)\n)",
    "CREATE TABLE public.ref_locales (\n\tcode VARCHAR(64) NOT NULL, \n\tlanguage_code VARCHAR(8) NOT NULL, \n\tscript_code VARCHAR(4), \n\tregion_code VARCHAR(3), \n\tcountry_code VARCHAR(2), \n\tname VARCHAR(255) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (code), \n\tFOREIGN KEY(country_code) REFERENCES public.ref_countries (code)\n)",
    "CREATE TABLE tenant_domains (\n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tservice_type VARCHAR(32) NOT NULL, \n\tkind VARCHAR(32) NOT NULL, \n\thost VARCHAR(255) NOT NULL, \n\tbase_path VARCHAR(255), \n\tauth_mode VARCHAR(32), \n\tstatus VARCHAR(32) DEFAULT 'active' NOT NULL, \n\tis_primary BOOLEAN NOT NULL, \n\tis_wildcard BOOLEAN NOT NULL, \n\tparent_domain VARCHAR(255), \n\tverification_status VARCHAR(32) DEFAULT 'verified' NOT NULL, \n\ttls_mode VARCHAR(32) DEFAULT 'managed' NOT NULL, \n\tmetadata_json JSONB, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_saas_tenant_service_domain UNIQUE (tenant_id, service_type, host, base_path), \n\tFOREIGN KEY(tenant_id) REFERENCES tenants (id)\n)",
    "CREATE UNIQUE INDEX ix_tenant_domains_host ON tenant_domains (host)",
    "CREATE INDEX ix_tenant_domains_is_primary ON tenant_domains (is_primary)",
    "CREATE INDEX ix_tenant_domains_kind ON tenant_domains (kind)",
    "CREATE INDEX ix_tenant_domains_service_type ON tenant_domains (service_type)",
    "CREATE INDEX ix_tenant_domains_status ON tenant_domains (status)",
    "CREATE INDEX ix_tenant_domains_tenant_id ON tenant_domains (tenant_id)",
)


def upgrade() -> None:
    """Создаёт актуальную структуру и обязательные начальные данные."""
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    """Запрещает удаление public-данных при откате приложения."""
    raise RuntimeError(
        "Public schema downgrade is intentionally unsupported; preserve tenant data."
    )
