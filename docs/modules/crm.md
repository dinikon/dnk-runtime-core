# CRM

CRM backend is being rebuilt. Only SQLAlchemy models and their package exports remain:

- `ContactModel` and `CompanyModel` in `src/modules/crm/infrastructure/persistence/models.py`.
- `ContactCompanyModel` in `src/modules/crm/links/infrastructure/persistence/models.py`.

The `contacts`, `companies` and `contact_companies` tables retain their columns, constraints,
indexes and foreign keys. All three models remain registered through `src/modules/tenant_persistence.py`
so Alembic continues to include them in tenant metadata. Existing migrations remain unchanged;
this backend cleanup requires no new migration and does not modify stored data.

The domain, application, repositories, adapters and HTTP/DI layers have been removed, including
those in `crm/links`. `/api/console/crm/*` endpoints are absent from OpenAPI and return `404`.
The independent `contact_points` module remains available, including its label API and storage.

Console CRM screens remain in place for the rebuild. Their CRM requests will return `404` until
the backend API is implemented again.

Do not use the historical [CRM removal runbook](../operations/remove-crm.md) for this cleanup:
it describes destructive database removal, whereas the current change preserves the SQL schema.
