# Contact Point And Object Feature Removal Runbook

This release permanently removes the `contact_point` module and the `schema_registry.object_feature` subdomain.
No data export, compatibility layer or in-place database migration is provided.

## Maintenance Sequence

1. Stop the API, management processes and workers that can access the application database.
2. Deploy the new release without starting its processes.
3. Drop and recreate the application database, including all tenant schemas.
4. Start the application so the system tables are created from the new SQLAlchemy metadata.
5. Recreate tenants so their runtime schemas are bootstrapped from the new default seed.

## Verification

The system table must not exist:

```sql
SELECT to_regclass('public.object_feature_config');
```

The query must return no rows for any schema:

```sql
SELECT schemaname, tablename
FROM pg_tables
WHERE tablename IN ('contact_points', 'contact_point_bindings');
```

Confirm that `/api/console/contact-points` and `/api/console/config/objects/features` are absent from OpenAPI and
representative requests under both prefixes return `404`.
