# Workflow And Communication Removal Runbook

This runbook applies the destructive environment reset after deploying the release that removes the workflow and
communication modules. The procedure does not export, migrate or preserve application, tenant, event or broker data.

## Preconditions

- Treat every target environment as disposable.
- Confirm that losing the application database, all tenant schemas, Redis state and RabbitMQ messages is acceptable.
- Remove all `COMMUNICATION_QUEUE__*` variables from deployment configuration.
- Keep the shared `RABBITMQ__*`, `EVENT_BUS__*` and `SCHEDULED_JOBS__*` configuration used by the remaining services.

## Reset Sequence

1. Stop the API, frontend, event workers, scheduled-job workers and any external writers.
2. Deploy the release without starting application processes.
3. Drop and recreate the application PostgreSQL database. This removes system metadata and all tenant schemas.
4. Recreate the RabbitMQ vhost or broker storage. This removes old communication exchanges, queues, bindings and
   messages together with shared event queues, which will be recreated by the remaining topology setup.
5. Clear Redis when rebuilding the complete environment so no sessions or tokens reference deleted database rows.
6. Start PostgreSQL, Redis and RabbitMQ, then start the API and shared event workers.
7. Recreate tenants. The default seed creates an empty tenant runtime schema with `code="runtime"`, `label="Runtime"`
   and no predefined system objects.
8. Start the Console and verify authentication, tenant resolution and schema configuration flows.

For the local Docker Compose environment, the equivalent operation is a complete project teardown including volumes,
followed by `docker compose up --build`. Run it only after confirming that all local volume data may be discarded.

## Verification

- OpenAPI contains no paths beginning with `/api/console/workflows` or `/api/console/communication`.
- Requests to representative removed endpoints return `404`.
- `dnk-manage --help` does not list a `communication` command group.
- The application configuration exposes no `COMMUNICATION_QUEUE` settings group.
- Newly created tenant schemas contain no workflow or communication tables.
- Schema metadata contains no workflow or communication objects, fields or relations.
- RabbitMQ contains no exchanges or queues with the `communication.` prefix.
- The shared event exchange and its active consumer queues are recreated successfully.
- Console routes under `/workflows` and `/cdp` resolve through the application fallback instead of loading removed UI.

## Removed Runtime Tables

The reset removes the former workflow tables `workflow_applications` and `workflow_definitions`, plus all tables with
the `communication_` prefix, including provider connectors/connections, templates, outbound messages, delivery attempts
and delivery events.
