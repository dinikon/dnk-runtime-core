# CRM Removal Runbook

This runbook applies the destructive cleanup after deploying the release that no longer contains the CRM module.
CRM records are not exported or backed up by this procedure.

## Maintenance Sequence

1. Stop API writers, `events-publisher` and `events-console-worker`.
2. Deploy the release with the CRM-free default schema seed.
3. Apply the destructive tenant schema diff:

   ```bash
   dnk-manage schema-registry diff --all
   ```

4. Remove historical and pending CRM integration events from the system database:

   ```sql
   BEGIN;
   DELETE FROM integration_inbox_events
   WHERE event_type LIKE 'crm.contact.%';
   DELETE FROM integration_outbox_events
   WHERE event_type LIKE 'crm.contact.%'
      OR aggregate_type = 'crm.contact';
   COMMIT;
   ```

5. Set `EVENTS_CONSOLE_QUEUE_NAME=dnk.integration.events.console` and `EVENTS_CONSOLE_ROUTING_KEY=#` in the deployment
   environment. Delete the durable RabbitMQ queue `crm.contact.events` and its binding through RabbitMQ management.
6. Restart the API and event workers.

## Verification

The following queries must return no rows:

```sql
SELECT schemaname, tablename
FROM pg_tables
WHERE tablename IN ('contacts', 'companies', 'contacts_companies');

SELECT tenant_id, singular_name, plural_name
FROM objects
WHERE singular_name IN ('contact', 'company')
   OR plural_name IN ('contacts', 'companies');

SELECT tenant_id, name
FROM relations
WHERE name = 'contact_companies';

SELECT event_type
FROM integration_outbox_events
WHERE event_type LIKE 'crm.contact.%'
   OR aggregate_type = 'crm.contact';

SELECT event_type
FROM integration_inbox_events
WHERE event_type LIKE 'crm.contact.%';
```

Confirm that `/api/console/crm/contacts` and `/api/console/crm/companies` return `404` and are absent from OpenAPI.
